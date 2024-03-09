# Minecraft Username Checker

This Python script checks the availability of Minecraft usernames and sends notifications to Discord when a username becomes available or enters different stages of the 37-day grace period.

## Features

- Checks the availability of specified Minecraft usernames
- Sends Discord notifications when a username becomes available
- Provides updates at different stages of the 37-day grace period
- Customizable configuration through environment variables
- Docker support for easy deployment

## Configuration

The script uses environment variables for configuration. You can set the following variables:

- `MINECRAFT_USERNAMES`: Comma-separated list of Minecraft usernames to check
- `DISCORD_WEBHOOK_URL`: Discord webhook URL for sending notifications
- `DISCORD_USER_ID`: Discord user ID to mention in notifications

## Usage with Docker

```yaml
version: '3'

services:
  minecraft-username-checker:
    image: ghcr.io/itslightmind/minecraft-username-checker:latest
    environment:
      - MINECRAFT_USERNAMES=username1,username2
      - DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/XXXX/XXXX"
      - DISCORD_USER_ID="YOUR_USER_ID"
    volumes:
      - ./available_usernames.json:/app/available_usernames.json
```