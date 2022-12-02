class Notion::UpdateRecurringTaskTime
  attr_accessor :task

  def initialize(task)
    self.task = task
  end

  def update_task
    db_client = Notion::DatabaseClient.new(Settings.notion.databases.tasks)
    task.time_mark = task.next_time_by_recurring_type&.in_time_zone
    return if task.time_mark.nil? || (task.end_time.present? && task.time_mark > task.end_time)

    task.is_done = false
    db_client.update_page(task.notion_object_id, task.to_data)
  end
end
