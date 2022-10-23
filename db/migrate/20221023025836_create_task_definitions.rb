class CreateTaskDefinitions < ActiveRecord::Migration[7.0]
  def change
    create_table :task_definitions do |t|
      t.references :interval_type, index: true
      t.string :notion_database_id, index: true
      t.string :task_name
      t.string :type_of_task, index: true
      t.text :content
      t.datetime :start_time
      t.datetime :end_time

      t.timestamps
    end
  end
end
