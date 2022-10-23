class PersonalSidekiqHandler
  def call(exception, context_hash)
    # This will be a chatbot that send to Messenger
  end
end

Sidekiq.configure_server do |config|
  config.redis = { url: "redis://#{ENV["REDIS_HOST"]}/0" }
  config.error_handlers << PersonalSidekiqHandler
end

Sidekiq.configure_client do |config|
  config.redis = { url: "redis://#{ENV["REDIS_HOST"]}/0" }
end
