class Notion::TaskPolling
  include ActionView::Helpers::DateHelper

  DEADLINE_COMMENT_MESSAGE = "Task `%s` is over deadline!!!"

  def self.singleton
    @singleton ||= new
  end

  def db_client
    @db_client ||= Notion::DatabaseClient.new(Settings.notion.databases.tasks)
  end

  def execute
    notion_done_tasks_data = db_client.retrieve_pages(
      filter: {
        or: [
          {
            and: [
              {
                property: Settings.notion.definition_fields.is_done,
                checkbox: {
                  equals: true
                }
              },
              {
                property: Settings.notion.definition_fields.recurring_type,
                select: {
                  does_not_equal: "once"
                }
              }
            ]
          },
          {
            and: [
              {
                property: Settings.notion.definition_fields.is_done,
                checkbox: {
                  equals: false
                }
              },
              {
                property: Settings.notion.definition_fields.deadline,
                date: {
                  is_not_empty: true
                }
              }
            ]
          },
          {
            and: [
              {
                property: Settings.notion.definition_fields.is_done,
                checkbox: {
                  equals: false
                }
              },
              {
                property: Settings.notion.definition_fields.remind,
                checkbox: {
                  equals: true
                }
              }
            ]
          }
        ]
      }
    )
    tasks = Task.from_data(notion_done_tasks_data)

    tasks.each do |task|
      update_recurring_time(task)
      post_deadline_remind_message(task)
      post_task_reminder_message(task)
    end
  end

  def update_recurring_time(task)
    return unless task.is_done && task.valid? && task.recurring_type != "once"

    Notion::UpdateRecurringTaskTime.new(task).update_task
  end

  def post_deadline_remind_message(task)
    current_time = Settings.mode.skip_time ? Time.zone.now.beginning_of_day : Time.zone.now
    return unless !task.is_done && task.deadline.present? && task.deadline <= current_time

    db_client.add_comment(task.notion_object_id, DEADLINE_COMMENT_MESSAGE % task.task_name)
  end

  def post_task_reminder_message(task)
    return if task.is_done || !task.remind
    return if task.time_mark < Time.zone.now || 15.minutes.from_now < task.time_mark

    reminder_message = "Task #{task.task_name} is should be started in "\
                       "#{distance_of_time_in_words_to_now(task.time_mark)} (#{task.time_mark.strftime('%H:%M')})"
    db_client.add_comment(task.notion_object_id, reminder_message)
  end
end
