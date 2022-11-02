class NotionModel < ApplicationModel
  attribute :notion_object_id, :string
  attr_accessor :raw_data

  validates :notion_object_id, presence: true

  def to_data
    result = raw_data.deep_dup

    self.class.attribute_names_mapping.each do |attr_name, property_name|
      data_type = result.dig(property_name, "type")

      case data_type
      when "select"
        result[property_name]["select"]["name"] = send(attr_name)
      when "date"
        old_date = result[property_name]["date"]
        new_date = send(attr_name)&.iso8601
        next if old_date.blank? && new_date.blank?

        old_date["start"] = new_date
      when "checkbox"
        result[property_name]["checkbox"] = send(attr_name)
      when "title"
        result[property_name]["title"][0]["text"]["content"] = send(attr_name).to_s
        result[property_name]["title"][0]["plain_text"] = send(attr_name).to_s
      else
        next
      end
    end
    result
  end

  class << self
    def from_data(json_data)
      return new_from_json(json_data) if json_data.is_a?(Hash)
      return json_data.map(&method(:new_from_json)) if json_data.is_a?(Array)

      nil
    end

    def to_data(collection)
      collection.each { |item| item.to_data }
    end

    def new_from_json(json_data)
      model_properties = properties_by_type(
        json_data["properties"].slice(*attribute_names_mapping.values)
      )
      new(
        notion_object_id: json_data["id"],
        **model_properties,
        raw_data: json_data["properties"]
      )
    end

    def attribute_names_mapping
      if self.name != NotionModel.name
        raise "attribute_names_mapping must be overwrite"
      end

      {}
    end

    def properties_by_type(prop_raw_data)
      result = {}
      prop_raw_data.inject(result) do |hash, (attribute_name, value_obj)|
        attr_key = attribute_names_mapping.key(attribute_name)

        case value_obj["type"]
        when "select"
          hash[attr_key] = value_obj.dig("select", "name")
        when "date"
          hash[attr_key] = value_obj.dig("date", "start")
          end_time = value_obj.dig("date", "end")
          hash[attribute_names_mapping.key("#{attribute_name} end")] = end_time if end_time.present?
        when "checkbox"
          hash[attr_key] = value_obj["checkbox"]
        when "title"
          hash[attr_key] = value_obj.dig("title", 0, "plain_text")
        else
          hash[attr_key] = nil
        end
        hash
      end
      result
    end
  end
end
