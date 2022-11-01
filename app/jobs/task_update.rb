class TaskUpdate < ApplicationJob
  queue_as :task_update

  def perform
    Notion::TaskPolling.execute
  end
end
