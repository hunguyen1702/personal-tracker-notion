class TaskUpdate < ApplicationJob
  queue_as :task_update

  def perform
    Notion::TaskPolling.singleton.execute
    puts "[#{Time.zone.now}] Tasks list have been updated"
  end
end
