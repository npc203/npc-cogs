from difflib import ndiff
from pathlib import Path
from random import randint, sample

from fuzzywuzzy import fuzz
from redbot.core import commands
from tabulate import tabulate
from redbot.core.utils.mod import is_mod_or_superior

# can't use bundled_data_path cause outside class
path = Path(__file__).absolute().parent / "data"
data = {}

# https://www.mit.edu/~ecprice/wordlist.10000
with open(path / "filtered.txt", "r", encoding="utf8") as f:
    data["gibberish"] = f.read().split()

# https://raw.githubusercontent.com/ccpalettes/sublime-lorem-text/master/wordlist/word_list_fixed.txt
with open(path / "lorem.txt", "r", encoding="utf8") as f:
    data["lorem"] = f.read().split()


def typerset_check():
    async def predicate(ctx):
        if ctx.guild is None:
            return True
        return (
            # Owner check cause is_mod_or_superior doesn't respect it
            (ctx.author.id == ctx.bot.owner_id)
            # Mod or higher
            or (await is_mod_or_superior(ctx.bot, ctx.author))
            # Guild Admin
            or ctx.channel.permissions_for(ctx.author).administrator
        )

    return commands.check(predicate)


async def evaluate(ctx, a_string: str, b_string: str, time_taken, dm_id, author_name=None):
    """Returns None on personal event, returns [time_taken,wpm,mistakes] on speedevents"""
    user_obj = ctx.guild.get_member(dm_id) if dm_id else ctx.author
    special_send = user_obj.send if dm_id else ctx.send
    if not author_name:
        author_name = ctx.author.display_name

    if "​" in b_string:
        if not dm_id:
            await special_send("Imagine cheating bruh, c'mon atleast be honest here.")
        else:
            await special_send("You cheated and hence you are disqualified.")
        return
    else:
        mistakes = 0
        for i, s in enumerate(ndiff(a_string, b_string)):
            if s[0] == " ":
                continue
            elif s[0] in ["-", "+"]:
                mistakes += 1
    # Analysis
    accuracy = fuzz.ratio(a_string, b_string)
    wpm = len(a_string) / 5 / (time_taken / 60)
    if accuracy > 66:  # TODO add to config
        verdict = [
            (
                "WPM (Correct Words per minute)",
                wpm - (mistakes / (time_taken / 60)),
            ),
            ("Raw WPM (Without accounting mistakes)", wpm),
            ("Accuracy(Levenshtein)", accuracy),
            ("Words Given", len(a_string.split())),
            (f"Words from {author_name}", len(b_string.split())),
            ("Characters Given", len(a_string)),
            (f"Characters from {author_name}", len(b_string)),
            (f"Mistakes done by {author_name}", mistakes),
        ]
        await special_send(content="```" + tabulate(verdict, tablefmt="fancy_grid") + "```")
        return [time_taken, wpm - (mistakes / (time_taken / 60)), mistakes]
    else:
        await special_send(
            f"{'You' if dm_id else author_name}  didn't want to complete the challenge."
        )


async def get_text(settings) -> tuple:
    """Gets the paragraph for the test"""
    length = randint(settings["text_size"][0], settings["text_size"][1])
    a_string = " ".join(sample(data[settings["type"]], length)) + "."
    return (a_string, 1)


def nocheats(text: str) -> str:
    """To catch Cheaters upto some extent"""
    text_list = list(text)
    size = len(text)
    for _ in range(size // 5):
        text_list.insert(randint(0, size), "​")
    return "".join(text_list)
