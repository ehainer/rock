FROM ruby:$ruby

LABEL maintainer="Eric Hainer <eric@commercekitchen.com>"

# Set the root directory of the app within the container
ENV APP_ROOT /web

# Configure Bundler
ENV GEM_HOME=/bundle
ENV BUNDLE_PATH=/bundle
ENV BUNDLE_GEMFILE=$APP_ROOT/Gemfile
ENV BUNDLE_JOBS=2
ENV PATH="${BUNDLE_BIN}:${PATH}"

# Update and Install Dependencies
RUN apt-get update -qq
RUN apt-get install -y build-essential
RUN apt-get install -y libpq-dev
RUN apt-get install -y tzdata
RUN apt-get install -y libxml2-dev
RUN apt-get install -y libxslt-dev
RUN apt-get install -y nodejs
RUN apt-get install -y libqt4-dev
RUN apt-get install -y xvfb
RUN apt-get install -y git
RUN apt-get install -y ssh

# Clean out apt cache, helps keep image size down
RUN rm -rf /var/lib/apt/lists/*

# Create the root directory to the app
RUN mkdir -p $APP_ROOT

# Add necessary Gemfiles so `bundle install` can run
ADD Gemfile $APP_ROOT/Gemfile
ADD Gemfile.lock $APP_ROOT/Gemfile.lock

# Install Gems
RUN bundle install