class TaskPollingJob < ApplicationJob
  queue_as :task_polling

  def perform
  end
end
