class Task < NotionModel
  attribute :time_mark, :datetime
  attribute :deadline, :datetime
  attribute :is_done, :boolean
  attribute :recurring_type, :string

  class << self
    def attribute_names_mapping
      Settings.notion.definition_fields.to_h
    end
  end
end
