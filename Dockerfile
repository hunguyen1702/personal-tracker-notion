FROM ruby:3.0-alpine3.16

RUN apk update \
    && apk --no-cache --update add build-base tzdata

WORKDIR /app

COPY Gemfile /app
COPY Gemfile.lock /app

RUN bundle install

COPY . /app/
