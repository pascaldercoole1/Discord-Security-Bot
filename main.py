import discord
import os
import pytz
import time
import threading
import datetime
from discord.ext import commands, tasks
import asyncio
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!S', intents=intents)

# Deaktiviere den eingebauten Hilfe-Befehl
bot.remove_command('help')

## SETTINGS ##
BotVersion = "1.0"  # Setze hier deine Bot-Version ein
MAX_MEMBERS_PER_INTERVAL = 10
INTERVAL_DURATION = 10  # in seconds
SPAM_MESSAGE_THRESHOLD = 6
SPAM_CHANNEL_LOCK_DURATION = 10  # 300 in seconds (5 minutes)
## SETTINGS ##

## TEST ##

## I NEED TO DO THAT BECAUSE RENDER DOESNT SAVE MY FILES!!!

guild_id = 1221843659662819388
directory = f"Guilds/VerifyRole/"
if not os.path.exists(directory):
    os.makedirs(directory)

path = f"{directory}{guild_id}"
with open(path, "w") as file:
    file.write(str(1237108783591718976))

## TEST ##

join_counter = 0

# Ein Dictionary zum Speichern von Nachrichten pro Mitglied und Kanal
user_messages_dict = {}
similar_messages = []

SIMILARITY_THRESHOLD = 0.8  # Schwellenwert für Ähnlichkeit


def is_similar(message1, message2):
  return message1.content.lower().strip() == message2.content.lower().strip()


@bot.event
async def on_ready():
  print(f'Logged in as {bot.user.name}!')

  # Aktivität des Bots ändern
  activity = discord.Activity(type=discord.ActivityType.watching,
                              name='for Raids')
  await bot.change_presence(activity=activity)

  check_intervals.start()


@bot.event
async def on_member_join(member):
  global join_counter
  join_counter += 1


@tasks.loop(seconds=INTERVAL_DURATION)
async def check_intervals():
  global join_counter
  if join_counter > MAX_MEMBERS_PER_INTERVAL:
    for guild in bot.guilds:
      for member in guild.members:
        if not member.bot and member.joined_at > datetime.datetime.utcnow(
        ) - datetime.timedelta(seconds=INTERVAL_DURATION):
          time.sleep(0.1)
          await member.kick(
              reason='Too many members joined within a short interval.')
          join_counter -= 1


async def check_mass_spam(member, channel, message):
  now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
  if member in user_messages_dict and channel in user_messages_dict[member]:
    messages_in_last_minute = [
        msg for msg in user_messages_dict[member][channel]
        if now - msg.created_at < datetime.timedelta(minutes=1)
    ]
    if len(messages_in_last_minute) > 100:
      ## await channel.send("Massen-Spam Detected! Locking Channel...")

      # Verifizierungsrolle auslesen oder Standardrolle verwenden
      guild_id = str(channel.guild.id)
      role_path = f"Guilds/VerifyRole/{guild_id}"
      default_role = channel.guild.default_role
      try:
        with open(role_path, "r") as file:
          role_id = int(file.read())
          role = channel.guild.get_role(role_id)
          if role is None:
            role = default_role
      except FileNotFoundError:
        role = default_role

      # Den Channel für die Verifizierungsrolle sperren
      overwrite = channel.overwrites_for(role)
      overwrite.send_messages = False
      await channel.set_permissions(role, overwrite=overwrite)

      await asyncio.sleep(SPAM_CHANNEL_LOCK_DURATION)

      # Den Channel entsperren
      overwrite.send_messages = True
      await channel.set_permissions(role, overwrite=overwrite)


@bot.event
async def on_message(message):
  if message.author.bot:
    return

  member = message.author
  channel = message.channel

  if not channel:
    return

  # Prüfe auf Ratelimit des Bots
  if bot.is_ws_ratelimited():
    ##await channel.send("Der Bot hat das Ratelimit erreicht. Der Channel wird vorübergehend gesperrt.")

    # Den Channel für @everyone sperren
    overwrite = channel.overwrites_for(channel.guild.default_role)
    overwrite.send_messages = False
    await channel.set_permissions(channel.guild.default_role,
                                  overwrite=overwrite)

    await asyncio.sleep(SPAM_CHANNEL_LOCK_DURATION)

    # Den Channel entsperren
    overwrite.send_messages = None
    await channel.set_permissions(channel.guild.default_role,
                                  overwrite=overwrite)

    # Den Rest des Codes in dieser Funktion überspringen, wenn der Channel gesperrt ist
    return

  asyncio.create_task(check_mass_spam(member, channel, message))

  # Speichere die Nachrichten des Mitglieds im Kanal
  if member not in user_messages_dict:
    user_messages_dict[member] = {}
  if channel not in user_messages_dict[member]:
    user_messages_dict[member][channel] = []
  user_messages_dict[member][channel].append(message)

  try:
    if len(user_messages_dict[member][channel]) > SPAM_MESSAGE_THRESHOLD:
      # Lock the channel
      print("Spammer Found and Timeouted!")
      ##await channel.send("Spammer Found and Timeouted!")

      overwrite = channel.overwrites_for(member)
      overwrite.send_messages = False
      await channel.set_permissions(member, overwrite=overwrite)

      await asyncio.sleep(SPAM_CHANNEL_LOCK_DURATION)

      # Unlock the channel
      overwrite.send_messages = None
      await channel.set_permissions(member, overwrite=overwrite)

      # Check if the keys exist before deleting
      if member in user_messages_dict and channel in user_messages_dict[member]:
        del user_messages_dict[member][channel]

  except discord.errors.HTTPException as e:
    if e.code == 429:
      ##await channel.send("The bot is currently experiencing a high load. The channel will be locked temporarily.")
      overwrite = channel.overwrites_for(channel.guild.default_role)
      overwrite.send_messages = False
      await channel.set_permissions(channel.guild.default_role,
                                    overwrite=overwrite)

      await asyncio.sleep(SPAM_CHANNEL_LOCK_DURATION)

      # Unlock the channel
      overwrite.send_messages = None
      await channel.set_permissions(bot.guild.default_role,
                                    overwrite=overwrite)

  await bot.process_commands(message)


@commands.cooldown(1, 10, commands.BucketType.user)
@bot.command()
async def ping(ctx):
  latency = round(bot.latency * 1000)  # Wandelt Latenz in Millisekunden um
  print(f"Pong! Latency: {latency}ms")
  await ctx.send(f'Pong! Latency: {latency}ms')


# Cooldown Decorator mit 1 Sekunde
@commands.cooldown(1, 3, commands.BucketType.user)
@bot.command()
async def version(ctx):
  await ctx.send(f'Bot Version: {BotVersion}')


@bot.command()
@commands.has_permissions(administrator=True)
async def change_verify_role(ctx, role_id: int):
  # Verifiziere, dass die gegebene RolenID gültig ist
  role = ctx.guild.get_role(role_id)
  if role is None:
    await ctx.send(
        "Ungültige RolenID. Bitte überprüfe die ID und versuche es erneut.")
    return

  # Speichere die RolenID im angegebenen Pfad
  guild_id = str(ctx.guild.id)
  path = f"Guilds/VerifyRole/{guild_id}"
  with open(path, "w") as file:
    file.write(str(role_id))

  await ctx.send(
      f"Die Verifizierungsrolle wurde erfolgreich auf '{role.name}' gesetzt!")


@bot.command()
@commands.has_permissions(administrator=True)
async def lock(ctx):
  # Verifizierungsrolle auslesen oder Standardrolle verwenden
  guild_id = str(ctx.guild.id)
  role_path = f"Guilds/VerifyRole/{guild_id}"
  default_role = ctx.guild.default_role
  try:
    with open(role_path, "r") as file:
      role_id = int(file.read())
      role = ctx.guild.get_role(role_id)
      if role is None:
        role = default_role
  except FileNotFoundError:
    role = default_role

  # Den Channel für die Verifizierungsrolle sperren
  overwrite = ctx.channel.overwrites_for(role)
  overwrite.send_messages = False
  await ctx.channel.set_permissions(role, overwrite=overwrite)
  await ctx.send(f"Channel locked! (for role: {role.name})")


@bot.command()
@commands.has_permissions(administrator=True)
async def unlock(ctx):
  # Verifizierungsrolle auslesen oder Standardrolle verwenden
  guild_id = str(ctx.guild.id)
  role_path = f"Guilds/VerifyRole/{guild_id}"
  default_role = ctx.guild.default_role
  try:
    with open(role_path, "r") as file:
      role_id = int(file.read())
      role = ctx.guild.get_role(role_id)
      if role is None:
        role = default_role
  except FileNotFoundError:
    role = default_role

  # Den Channel für die Verifizierungsrolle entsperren
  overwrite = ctx.channel.overwrites_for(role)
  overwrite.send_messages = True
  await ctx.channel.set_permissions(role, overwrite=overwrite)
  await ctx.send(f"Channel unlocked! (for role: {role.name})")


@bot.command()
@commands.has_permissions(administrator=True)
async def clear(ctx, amount: int):
  if amount > 0:
    deleted = await ctx.channel.purge(limit=amount + 1)
  else:
    await ctx.send(f'Please use an Amount (example: !clear 10)',
                   delete_after=5)


@bot.command()
@commands.has_permissions(administrator=True)
async def unlockuser(ctx, member: discord.Member):
  # Den Channel für den Benutzer entsperren
  overwrite = ctx.channel.overwrites_for(member)
  overwrite.send_messages = None
  await ctx.channel.set_permissions(member, overwrite=overwrite)

  await ctx.send(f"Channel unlocked for {member.mention}.")


@bot.command()
@commands.has_permissions(administrator=True)
async def unlockallusers(ctx):
  # Iteriere über alle Benutzer, um die Berechtigungsüberschreibungen zu entfernen
  for member in ctx.guild.members:
    overwrite = ctx.channel.overwrites_for(member)
    if overwrite.send_messages is not None:
      overwrite.send_messages = None
      await ctx.channel.set_permissions(member, overwrite=overwrite)

  await ctx.send("Channel unlocked for all users.")


keep_alive()
bot.run(os.environ['TOKEN'])
