class Notion::TaskPolling
  DEADLINE_COMMENT_MESSAGE = "Task `%s` is over deadline!!!"

  def self.execute
    db_client = Notion::DatabaseClient.new(Settings.notion.databases.tasks)
    notion_done_tasks_data = db_client.retrieve_pages
    tasks = Task.from_data(notion_done_tasks_data)

    tasks.each do |task|
      if task.is_done && task.valid? && task.recurring_type != "once"
        Notion::UpdateRecurringTaskTime.new(task).update_task
      end
      if !task.is_done && task.deadline.present? && task.deadline <= Time.zone.now
        db_client.add_comment(task.notion_object_id, DEADLINE_COMMENT_MESSAGE % task.task_name)
      end
    end
  end
end
