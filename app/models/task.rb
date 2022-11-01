class Task < NotionModel
  attribute :time_mark, :datetime
  attribute :end_time, :datetime
  attribute :is_done, :boolean
  attribute :recurring_type, :string, default: "once"

  validates :time_mark, presence: true
  validates :recurring_type, presence: true,
    inclusion: { within: %w[
      daily weekly monthly bi-daily
      bi-weekly bi-monthly annually once
    ] }

  def next_time_by_recurring_type
    case recurring_type
    when "daily"
      time_mark.next_day
    when "weekly"
      time_mark.next_week(Date::DAYNAMES[time_mark.wday].downcase.to_sym, same_time: true)
    when "monthly"
      time_mark.next_month
    when "bi-daily"
      time_mark.next_day(2)
    when "bi-weekly"
      week_day_name = Date::DAYNAMES[time_mark.wday].downcase.to_sym
      time_props = { same_time: true }
      time_mark
        .next_week(week_day_name, **time_props)
        .next_week(week_day_name, **time_props)
    when "bi-monthly"
      time_mark
        .next_month
        .next_month
    when "annually"
      time_mark.next_year
    when "once"
      time_mark
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
