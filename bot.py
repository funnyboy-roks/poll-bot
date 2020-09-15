import discord
from discord.ext import commands

TOKEN = open("TOKEN.txt", "r").read()

bot = commands.Bot(command_prefix='/poll ')

TEMP_MSG_ID = 755207557492113440 

@bot.event
async def on_ready():
    print(f'Logged in as: {bot.user.name}')
    print(f'With ID: {bot.user.id}')


@bot.command()
async def start(ctx, *msg):
    message = " ".join(msg)
    embedded_msg = discord.Embed(
        title="Title", description="Desc", color=0x51e2f5)
    embedded_msg.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
    embedded_msg.add_field(name="*Field1*", value=message, inline=False)
    embedded_msg.add_field(name="Field2", value="hi2", inline=False)
    await ctx.send(embed=embedded_msg)

@bot.event
async def on_raw_reaction_add(payload):
    # msg.edit
    print(payload)
    guil = payload.member.guild
    chan = guil.get_channel(payload.channel_id)
    msg = await chan.fetch_message(payload.message_id)
    if len(msg.embeds) == 1:
        emb = msg.embeds[0]
        emb.add_field(name="Emoji", value=payload.emoji.name)
        await msg.edit(embed=emb)

bot.run(TOKEN)
