# Npc-Cogs V3

[![Red-DiscordBot](https://img.shields.io/badge/Red--DiscordBot-V3-red.svg)](https://github.com/Cog-Creators/Red-DiscordBot)
[![Discord.py](https://img.shields.io/badge/Discord.py-rewrite-blue.svg)](https://github.com/Rapptz/discord.py/tree/rewrite)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

A fun oriented list of Red-Cogs made for fun and stonks.
Discord User: epic guy#0715
Docs: https://npc-cogs.readthedocs.io/en/latest

# Installation

To add cogs from this repo to your instance, do these steps:

- `[p]repo add npc-cogs https://github.com/npc203/npc-cogs`
- `[p]cog install npc-cogs <cog name>`
- `[p]load <cog name>`

## About Cogs

| Cog         | Status | Description                                                                                                                                                                                                             |
| ----------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bible       | Alpha  | <details><summary>Get bible verses or get references for words</summary>Powered by biblegateway, this cog can get bible verses and also can reverse search by getting the references for the searched word</details>    |
| CustomHelp  | Alpha  | <details><summary>A category themed custom help</summary>Kindly read https://npc-cogs.readthedocs.io/en/latest/customhelp.html on how to setup</details>                                                                |
| Google      | Alpha  | <details><summary>A google search cog with tons of functions</summary>This cog scrapes google to get results/reverse image search, cards, books, images, etc.. (siu3334 did a lotta work in this cog as well)</details> |
| NoReplyPing | Beta   | <details><summary>Notifies in dms if a person replies to you but turned their ping off</summary> Made for the servers with extra modesty who turn their pings off and you miss their message </details>                 |
| Speak       | Alpha  | <details><summary>Speak as others or for yourself</summary>This uses webhooks to mimic the person's identity and speak what you type, it also can speak stuff for you (insults and sadme)</details>                     |
| Todo        | Alpha  | <details><summary>A todo cog</summary>A simple todo cog to remember your tasks</details>                                                                                                                                |
| TypeRacer   | Alpha  | <details><summary>Typing speed test</summary>Test your typing skills with this cog</details>                                                                                                                            |
| Weeb        | Alpha  | <details><summary>Bunch of Otaku emoticons</summary>Expwess youw weebness using the bunch of wandom weeb emoticons UwU</details>                                                                                        |
| Snipe       | Alpha  | <details><summary>Multi Snipe for fun and non-profit</summary>Bulk sniping to stab back those anti-sniping smart ass users</details>                                                                                    |
| Snake       | Beta   | <details><summary>A simple Snake Game</summary>This is a classical snake game, uses dpy menus. Be fully aware of this cog spamming the channel ratelimit buckets</details>                                              |

## Credits

- Everyone who tested my cogs and helped me with the code. <3
- Everyone who contributed to make this better.
- Thank you Red community, you guys are awesome.

# Contributing

- Haven't set up pre-commit hooks yet, so if you want to contribute, please do it yourself.
- Kindly follow the format of black with line-length = 99 and isort
- This can be done by `pip install -U black isort`
- Then run the below commands to auto format your code

```py
black .
isort .
```
