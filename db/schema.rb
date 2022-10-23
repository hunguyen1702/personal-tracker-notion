# This file is auto-generated from the current state of the database. Instead
# of editing this file, please use the migrations feature of Active Record to
# incrementally modify your database, and then regenerate this schema definition.
#
# This file is the source Rails uses to define your schema when running `bin/rails
# db:schema:load`. When creating a new database, `bin/rails db:schema:load` tends to
# be faster and is potentially less error prone than running all of your
# migrations from scratch. Old migrations may fail to apply correctly if those
# migrations use external dependencies or application code.
#
# It's strongly recommended that you check this file into your version control system.

ActiveRecord::Schema[7.0].define(version: 2022_10_23_025836) do
  # These are extensions that must be enabled in order to support this database
  enable_extension "plpgsql"

  create_table "interval_types", force: :cascade do |t|
    t.string "name"
    t.datetime "date1"
    t.datetime "date2"
    t.datetime "date3"
    t.integer "offset"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
  end

  create_table "task_definitions", force: :cascade do |t|
    t.bigint "interval_type_id"
    t.string "notion_database_id"
    t.string "task_name"
    t.string "type_of_task"
    t.text "content"
    t.datetime "start_time"
    t.datetime "end_time"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["interval_type_id"], name: "index_task_definitions_on_interval_type_id"
    t.index ["notion_database_id"], name: "index_task_definitions_on_notion_database_id"
    t.index ["type_of_task"], name: "index_task_definitions_on_type_of_task"
  end

end
