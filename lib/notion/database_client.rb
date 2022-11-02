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

  def add_comment(page_id, content)
    comment_api_url = URI("https://api.notion.com/v1/comments")

    http = Net::HTTP.new(comment_api_url.host, comment_api_url.port)
    http.use_ssl = true

    request = Net::HTTP::Post.new(comment_api_url)
    request["accept"] = 'application/json'
    request["Notion-Version"] = '2022-06-28'
    request["content-type"] = 'application/json'
    request["authorization"] = "Bearer #{ENV["NOTION_SECRET_TOKEN"]}"
    request.body = {
      parent: {
        page_id: page_id
      },
      rich_text: [
        {
          text: {
            content: content
          }
        }
      ]
    }.to_json

    response = http.request(request)
    response.code == "200"
  end

  private

  def client
    @client ||= Notion::Client.new
  end
end
