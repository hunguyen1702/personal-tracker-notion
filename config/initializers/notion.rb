Notion.configure do |config|
  config.token = ENV["NOTION_SECRET_TOKEN"]
  config.default_page_size = 25
end
