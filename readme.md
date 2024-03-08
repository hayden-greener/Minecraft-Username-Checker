# Minecraft Username Checker

This Python script checks the availability of Minecraft usernames and sends notifications via Discord webhooks when usernames become available. It also handles the 30-day grace period before usernames are actually released and notifies the user if a username is retaken during that period.

## Features

- Checks the availability of Minecraft usernames using the Mojang API
- Sends notifications to a Discord webhook when usernames become available
- Generates random notification messages with emojis and username mentions
- Handles rate limiting for the Mojang API and Discord API
- Stores available usernames and their timestamps in a JSON file
- Checks the grace period for previously available usernames and sends notifications accordingly
- Notifies the user if a username is retaken during the grace period
- Provides a professional and user-friendly command-line interface

## Setup

1. Clone the repository: