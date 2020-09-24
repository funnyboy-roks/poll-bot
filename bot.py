import discord
import pymongo
import random
import datetime
from discord.ext import commands


mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
database = mongo_client["Poll_Bot_Storage"]

guild_info_col = database["guild_info"]

help_message_text = """
    HELP MESSAGE...
"""

TOKEN = open("TOKEN.txt", "r").read()

bot = commands.Bot(command_prefix='/poll ')

TEMP_MSG_ID = 755207557492113440


@bot.event
async def on_ready():
    print(f'Logged in as: {bot.user.name}')
    print(f'With ID: {bot.user.id}')


@bot.event
async def on_guild_join(guild):
    polls_channel = await guild.create_text_channel(
        "polls",
        reason="Initial Creation of the Poll channel by the Poll-Bot",
        topic="Where all polls will be shown and featured",
    )

    ### THIS WILL BE MADE AN EMBED LATER ###

    # polls_message = await polls_channel.send(content="Adding a poll is quite simple, ")
    # await polls_message.pin()
    # help_message = await polls_channel.send(content=help_message_text)
    # await help_message.pin()

    update_db(
        guild,
        polls_channel_id=polls_channel.id,
        # polls_message_id=polls_message.id,
        # help_message_id=help_message.id,
        polls=[]
    )

    print(f'Bot has been added to a guild! Guild Name: \"{guild.name}\"')


@bot.command()
async def create(ctx, *name):
    title = " ".join(name)

    query = {"guild_id": ctx.guild.id}
    db_info = guild_info_col.find_one(query)

    polls_list = db_info["polls"]

    original_poll = True
    for x in polls_list:
        if x["status"] != "END" and x["name"] == title:
            original_poll = False
    if len(name) > 0 and original_poll:
        new_poll = {
            "name": title,
            "description": "No Description",
            "message_id": 0,
            "date_created": datetime.datetime.now(),
            "author_id": ctx.author.id,
            "author_name": ctx.author.name,
            # "colour": random.randint(0, 16777215),
            "colour": 16528643,
            "status": "CREATED",
            "reactions": [],
            "voted_users": [],
        }

        guild = ctx.guild
        author = await guild.fetch_member(new_poll["author_id"])
        channel = guild.get_channel(db_info["polls_channel_id"])

        emb_dict = {
            "title": f'{new_poll["name"]} ',
            "description": f'`ID: {len(polls_list)}` - {new_poll["description"]}',
            "color": new_poll["colour"],
            "author": {
                "name": author.name,
                "icon_url": str(author.avatar_url)
            },
            "fields": [
                {
                    "name": "Almost Done!",
                    "value": f"{author.mention}, before your poll can start, you'll need to add votes by adding reactions to this message.",
                    "inline": False
                }
            ]
        }
        embedded_msg = discord.Embed.from_dict(emb_dict)

        sent_msg = await channel.send(embed=embedded_msg)
        new_poll["message_id"] = sent_msg.id

        polls_list.append(new_poll)
        update_db(g=guild, polls=polls_list)


@bot.command()
async def start(ctx, *name):

    query = {"guild_id": ctx.guild.id}
    db_info = guild_info_col.find_one(query)
    polls = db_info["polls"]

    title = " ".join(name)
    match = False
    started = False
    for i, x in enumerate(polls):
        if x["name"] == title:
            if x["status"] == "CREATED":
                x["colour"] = 261156
                x["status"] = "ACTIVE"

                update_db(g=ctx.guild, polls=polls)
                await ctx.send(f'Poll "`{x["name"]}`" started!', delete_after=10)
                await update_poll_embed(g=ctx.guild, poll_id=i, colour=x["colour"], poll=x)
                started = True
            match = True
            break
    if not match:
        await ctx.send(f'There was not a poll with the name "{title}".', delete_after=10)
    if not started:
        await ctx.send(f'The poll with the name {title} was not able to be started.')
    await ctx.message.delete()


@bot.event
async def on_raw_reaction_add(payload):
    if payload.member.id == bot.user.id:
        return

    guild = payload.member.guild
    channel = guild.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)

    query = {"guild_id": payload.guild_id}
    db_info = guild_info_col.find_one(query)

    polls_list = db_info["polls"]

    poll_message = False
    for x in range(len(polls_list)-1, -1, -1):
        global poll_id
        if polls_list[x]["message_id"] == payload.message_id:
            poll_id = x
            poll_message = True
            break
    if not poll_message:
        print(
            f'Reaction added to message by {str(payload.member)} was not a poll')
        return
    poll = polls_list[poll_id]

    if poll["status"] == "CREATED":  # If poll is CREATED, but not STARTED
        if poll["author_id"] == payload.member.id:
            for r in poll["reactions"]:
                if r["name"] == payload.emoji.name:
                    await message.remove_reaction(emoji=payload.emoji, member=payload.member)
                    return
            poll["reactions"].append({
                "name": payload.emoji.name,
                "id": payload.emoji.id,
                "count": 0,

            })
            polls_list[poll_id] = poll
            reactions = message.reactions
            for r in reactions:
                if not r.me:
                    await message.add_reaction(r.emoji)
                    await r.remove(payload.member)
            await update_poll_embed(g=payload.member.guild, poll_id=poll_id, poll=poll, emoji={
                "name": payload.emoji.name,
                "id": payload.emoji.id,
                "count": 0,
            })
            update_db(g=payload.member.guild, polls=polls_list)
        elif payload.member.id != bot.user.id:
            await message.remove_reaction(emoji=payload.emoji, member=payload.member)
            return

    elif poll["status"] == "ACTIVE":  # If poll is ACTIVE
        # try:
        await message.remove_reaction(emoji=payload.emoji, member=payload.member)

        for x in poll["voted_users"]:
            if x["user_id"] == payload.member.id and x["reaction_name"] == payload.emoji.name:
                print("User already voted!")
                return
        change_vote = False
        for i, x in enumerate(poll["voted_users"]):
            if x["user_id"] == payload.member.id and x["reaction_name"] != payload.emoji.name:
                change_vote = True
                change_vote_index = i
                break
        for i, r in enumerate(poll["reactions"]):
            if r["name"] == payload.emoji.name:
                r["count"] += 1
                if not change_vote:
                        poll["voted_users"].append({
                            "user_id": payload.member.id,
                            "reaction_choice": i,
                            "reaction_name": payload.emoji.name,
                        })
                else:
                    poll["reactions"][poll["voted_users"][change_vote_index]["reaction_choice"]]["count"] -= 1
                    poll["voted_users"][change_vote_index] = {
                        "user_id": payload.member.id,
                        "reaction_choice": i,
                        "reaction_name": payload.emoji.name,
                    }
                polls_list[poll_id] = poll
                update_db(g=payload.member.guild, polls=polls_list)
                await update_poll_embed(g=payload.member.guild, poll_id=poll_id, poll=poll)
                return
        # except Exception as e:
        #     print(e)


async def update_poll_embed(g=None, poll_id=None, emoji=None, colour=None, poll=None):
    if g != None:
        query = {"guild_id": g.id}
        db_info = guild_info_col.find_one(query)
        polls_list = db_info["polls"]
        poll_channel = g.get_channel(db_info["polls_channel_id"])

        if poll != None and poll_id != None:
            msg = await poll_channel.fetch_message(poll["message_id"])
            author = await g.fetch_member(poll["author_id"])
            emb_dict = {
                "title": f'{poll["name"]}',
                "description": f'`ID: {len(polls_list)}` - {poll["description"]}',
                "color": poll["colour"],
                "author": {
                    "name": author.name,
                    "icon_url": str(author.avatar_url)
                },
                "fields": []
            }
            if colour != None:
                emb_dict["colour"] = colour

            emoji_dict = {"name": "Votes: ", "value": ""}

            for x in poll["reactions"]:
                emoji_dict["value"] += f"{x['name']}: `{x['count']}` "

            # if emoji != None:
            #     emoji_dict["value"] += f"{emoji['name']}: `{emoji['count']}` "

            if len(poll["reactions"]) <= 1:
                emb_dict["fields"].append({"name": "Almost Done!",
                                           "value": f"{author.mention}, before your poll can start, you'll need to add votes by adding reactions to this message.",
                                           "inline": False})

            if emoji_dict["value"] == "" or emoji_dict["value"] == None:
                emoji_dict["value"] = "None"
            emb_dict["fields"].append(emoji_dict)
            emb = discord.Embed.from_dict(emb_dict)

            if len(msg.reactions) != len(poll["reactions"]):
                for r in msg.reactions:
                    await r.clear()

                for r in poll["reactions"]:
                    if r["id"] != None:
                        emoji = bot.get_emoji(r["id"])
                        await msg.add_reaction(emoji)
                    else:
                        await msg.add_reaction(r["name"])

            await msg.edit(embed=emb)


def update_db(g=None, **options):
    query = {}
    GUILD_DICT = {}
    if not g:
        for guild in bot.guilds:
            GUILD_DICT = {"guild_id": guild.id, "guild_name": guild.name, }
            for x in options:
                GUILD_DICT[x] = options[x]
            query = {"guild_id": guild.id}
    else:
        GUILD_DICT = {"guild_id": g.id, "guild_name": g.name, }
        for x in options:
            GUILD_DICT[x] = options[x]
        query = {"guild_id": g.id}
    if not guild_info_col.find_one(query):
        guild_info_col.insert_one(GUILD_DICT)
    else:
        guild_info_col.update_one(query, {"$set": GUILD_DICT})


bot.run(TOKEN)
