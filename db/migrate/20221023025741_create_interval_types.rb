class CreateIntervalTypes < ActiveRecord::Migration[7.0]
  def change
    create_table :interval_types do |t|
      t.string :name
      t.datetime :date1
      t.datetime :date2
      t.datetime :date3
      t.integer :offset

      t.timestamps
    end
  end
end
