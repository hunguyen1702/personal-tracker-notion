class IntervalType < ApplicationRecord
  has_many :task_definitions

  validate :sample_date_difference

  private

  def sample_date_difference
    return if (date_2.blank? && date_3.blank?) ||
      (date_1 != date_2 && date_2 != date_3 && date_3 != date_1)

    errors.add(:date_1, :sample_date_must_different)
  end
end
