class TaskDefinition < ApplicationRecord
  belongs_to :interval_type

  validates :task_name, :notion_database_id, :start_time, presence: true
end
