class NotionModel < ApplicationModel
  attribute :notion_object_id, :string

  class << self
    def from_data(json_data)
      return new_from_json(json_data) if json_data.is_a?(Hash)
      return json_data.map(&method(:new_from_json)) if json_data.is_a?(Array)

      nil
    end

    def new_from_json(json_data)
      model_properties = json_data["properties"].slice(*attribute_names_mapping.values)
      new(
        notion_object_id: json_data["id"],
        **model_properties
      )
    end

    def attribute_names_mapping
      if self.name != NotionModel.name
        raise "attribute_names_mapping must be overwrite"
      end

      {}
    end
  end
end
