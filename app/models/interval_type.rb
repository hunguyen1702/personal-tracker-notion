class IntervalType < ApplicationRecord
  has_many :task_definitions

  validates :name, uniqueness: true
  validate :sample_date_difference

  private

  def sample_date_difference
    return if ([date1, date2, date3].compact.blank?) ||
      (date1 != date2 && date2 != date3 && date3 != date1)

    errors.add(:date1, :sample_date_must_different)
  end
end
