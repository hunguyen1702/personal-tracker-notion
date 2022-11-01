class Notion::TaskPolling
  def self.execute
    db_client = Notion::DatabaseClient.new(Settings.notion.databases.tasks)
    filter_options = {
      property: Settings.notion.definition_fields.is_done,
      checkbox: {
        equals: true
      }
    }
    notion_done_tasks_data = db_client.retrieve_pages(filter: filter_options)
    tasks = Task.from_data(notion_done_tasks_data)

    tasks.each do |task|
      next if !task.valid? || task.recurring_type == "once"

      Notion::RecurringTask.new(task).update_task
    end
  end
end
