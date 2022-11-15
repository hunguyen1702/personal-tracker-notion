class Task < NotionModel
  attribute :task_name, :string
  attribute :time_mark, :datetime
  attribute :end_time, :datetime
  attribute :deadline, :datetime
  attribute :is_done, :boolean
  attribute :recurring_type, :string, default: "once"

  validates :time_mark, :task_name, presence: true
  validates :recurring_type, presence: true

  def next_time_by_recurring_type
    time_mark_in_zone = time_mark.in_time_zone
    case recurring_type
    when "daily"
      time_mark_in_zone.next_day
    when "weekly"
      time_mark_in_zone.next_week(Date::DAYNAMES[time_mark_in_zone.wday].downcase.to_sym, same_time: true)
    when "monthly"
      time_mark_in_zone.next_month
    when "bi-daily"
      time_mark_in_zone.next_day(2)
    when "bi-weekly"
      week_day_name = Date::DAYNAMES[time_mark_in_zone.wday].downcase.to_sym
      time_props = { same_time: true }
      time_mark
        .next_week(week_day_name, **time_props)
        .next_week(week_day_name, **time_props)
    when "bi-monthly"
      time_mark
        .next_month
        .next_month
    when "annually"
      time_mark_in_zone.next_year
    when "once"
      time_mark_in_zone
    when "weekday"
      next_time = time_mark_in_zone.next_day
      if next_time.on_weekend?
        next_time = next_time.next_week.change(
          hour: time_mark_in_zone.hour,
          min: time_mark_in_zone.min,
          sec: time_mark_in_zone.sec
        )
      end
      next_time
    when /\Aevery (?<number>\d) days\z/
      time_mark_in_zone + ($LAST_MATCH_INFO["number"].to_i + 1).days
    else
      nil
    end
  end

  class << self
    def attribute_names_mapping
      Settings.notion.definition_fields.to_h
    end
  end
end
