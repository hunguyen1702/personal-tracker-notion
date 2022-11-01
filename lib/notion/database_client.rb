class Notion::DatabaseClient
  DEFAULT_SLEEP_TIME = 5
  DEFAULT_MAX_RETRIES = 20

  attr_accessor :database_id

  def initialize(database_id)
    self.database_id = database_id
  end

  def retrieve_pages(**search_options)
    query_options = {
      sleep_interval: DEFAULT_SLEEP_TIME,
      max_retries: DEFAULT_MAX_RETRIES,
      database_id: database_id,
      **search_options
    }
    results = []
    client.database_query(query_options) do |page_list|
      pages = page_list.results
      pages_without_formula_prop = pages.map do |page|
        page["properties"] = page["properties"].reject { |_, prop| prop["type"] == "formula" }
        page
      end
      results.concat(pages_without_formula_prop)
    end
    results
  end

  def update_page(page_id, object)
    client.update_page(page_id: page_id, properties: object).present?
  end

  def create_page(object)
    client.create_page(parent: {database_id: database_id}, properties: object).present?
  end

  private

  def client
    @client ||= Notion::Client.new
  end
end
