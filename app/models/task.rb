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
    next_time_mark = next_recurring_time_of(time_mark)
    while next_time_mark.beginning_of_day < Time.zone.now.beginning_of_day
      current_time = next_time_mark
      next_time_mark = next_recurring_time_of(current_time)
    end

    next_time_mark
  end

  private

  def next_recurring_time_of(input_time)
    case recurring_type
    when "daily"
      input_time.next_day
    when "weekly"
      input_time.next_week(Date::DAYNAMES[input_time.wday].downcase.to_sym, same_time: true)
    when "monthly"
      input_time.next_month
    when "bi-daily"
      input_time.next_day(2)
    when "bi-daily-on-weekday"
      next_time = input_time.next_day(2)
      if next_time.on_weekend?
        next_time = next_time.next_day(2)
      end
      next_time
    when "bi-weekly"
      week_day_name = Date::DAYNAMES[input_time.wday].downcase.to_sym
      time_props = { same_time: true }
      input_time
        .next_week(week_day_name, **time_props)
        .next_week(week_day_name, **time_props)
    when "bi-monthly"
      input_time
        .next_month
        .next_month
    when "annually"
      input_time.next_year
    when "once"
      input_time
    when "weekday"
      next_time = input_time.next_day
      if next_time.on_weekend?
        next_time = next_time.next_week.change(
          hour: input_time.hour,
          min: input_time.min,
          sec: input_time.sec
        )
      end
      next_time
    when "weekend"
      next_time = input_time.next_day
      unless next_time.on_weekend?
        next_time = next_time.next_week(:saturday).change(
          hour: input_time.hour,
          min: input_time.min,
          sec: input_time.sec
        )
      end
      next_time
    when /\Aevery (?<number>\d) days\z/
      input_time + ($LAST_MATCH_INFO["number"].to_i + 1).days
    when "yearly"
      input_time.next_year
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
