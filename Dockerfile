FROM ruby:3.3-alpine3.20

RUN apk update \
    && apk --no-cache --update add build-base tzdata

WORKDIR /app

COPY Gemfile /app
COPY Gemfile.lock /app

RUN bundle install

RUN cp /usr/share/zoneinfo/Asia/Ho_Chi_Minh /etc/localtime
RUN echo "Asia/Ho_Chi_Minh" > /etc/timezone

COPY . /app/
