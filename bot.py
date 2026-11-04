import discord
from discord.ext import commands
import random
import asyncio

# --- الإعدادات الأساسية ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# --- قاعدة البيانات ---
WORDS_DATABASE = {
    "اكلات": ["منسف", "بيتزا", "شاورما", "كبسة", "فلافل", "سوشي", "مقلوبه", "مكموره", "لبنه وسنيوره"],
    "دول": ["الأردن", "مصر", "السعودية", "اليابان", "فرنسا", "تركيا", "قطر", "سوريا", "فلسطين", "المانيا", "العراق", "البرازيل"],
    "سيارات": ["بي ام دبليو", "مرسيدس", "بورش", "كيا", "لامبورغيني", "اودي", "رينج روفر", "تويوتا", "تيسلا", "فورد"],
    "رياضات": ["كرة قدم", "تنس طاوله", "تزلج", "كرة طائرة", "كرة سلة", "سباحة"],
    "اجهزة": ["تلفون/تابلت", "شاشة", "مايكروويف", "ثلاجة", "غسالة", "الرنين المغناطيسي", "ساعة", "لابتوب", "بلايستيشن"]
}

players = set()
scores = {}
votes = {}
is_game_running = False
out_player = None
secret_word = ""
current_category = ""

# متغيرات للتحكم بنظام الأدوار والأسئلة
turn_order = []
current_turn_index = 0

# --- 1️⃣ دالة بدء الجولة وتحديد الأدوار ---
async def start_round(channel):
    global is_game_running, out_player, secret_word, current_category, votes, turn_order, current_turn_index
    is_game_running = True
    votes = {}

    current_category = random.choice(list(WORDS_DATABASE.keys()))
    secret_word = random.choice(WORDS_DATABASE[current_category])

    player_list = list(players)
    out_player = random.choice(player_list)

    # إرسال الرسائل الخاصة للجميع
    for player in player_list:
        try:
            if player == out_player:
                embed = discord.Embed(
                    title="🤫 أنت برا السالفة!",
                    description=f"الفئة هي: **{current_category}**\nحاول تخمين الكلمة من كلام بقية اللاعبين دون أن يكتشفوك!",
                    color=discord.Color.red()
                )
            else:
                embed = discord.Embed(
                    title="🔍 أنت جوا السالفة!",
                    description=f"الفئة: **{current_category}**\nالكلمة السرية هي: **{secret_word}**\nحاول معرفة من هو الشخص الذي برا السالفة!",
                    color=discord.Color.green()
                )
            await player.send(embed=embed)
        except discord.Forbidden:
            await channel.send(f"⚠️ لم أتمكن من إرسال رسالة خاصة للـ {player.mention}.")

    await channel.send(
        f"🤫 **تم إرسال الأدوار بالخاص للجميع!**\n"
        f"**الفئة المعروضة للجميع هي:** `{current_category}`\n\n"
        f"🎯 **الآن سيبدأ دور الأسئلة بالترتيب!**"
    )

    # تجهيز ترتيب الأسئلة
    turn_order = player_list.copy()
    random.shuffle(turn_order)
    current_turn_index = 0

    await prompt_next_question(channel)

# --- دالة توجيه الدور للاعب التالي ---
async def prompt_next_question(channel):
    global current_turn_index
    
    if current_turn_index < len(turn_order):
        asker = turn_order[current_turn_index]
        target = turn_order[(current_turn_index + 1) % len(turn_order)]
        
        view = NextTurnView(asker)
        await channel.send(
            f"🗣️ **دور الأسئلة ({current_turn_index + 1}/{len(turn_order)}):**\n"
            f"يا {asker.mention} ➔ اسأل {target.mention} سؤالاً يتعلق بالفئة `{current_category}`!\n"
            f"*(بعد الانتهاء من السؤال والإجابة، اضغطوا على الزر أدناه للانتقال للدور التالي)*",
            view=view
        )
    else:
        await channel.send("✅ **انتهت جولة الأسئلة للجميع!** الان تناقشوا سريعاً واستعدوا للتصويت.")
        vote_view = VoteView(list(players))
        await channel.send(
            "🗳️ **اضغطوا على القائمة بالأسفل للتصويت على الشخص المشتبه به:**",
            view=vote_view
        )

# --- كلاس زر الانتقال للدور التالي ---
class NextTurnView(discord.ui.View):
    def __init__(self, current_asker):
        super().__init__(timeout=180)
        self.current_asker = current_asker

    @discord.ui.button(label="الانتقال للدور التالي ➡️", style=discord.ButtonStyle.primary)
    async def next_turn_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        global current_turn_index
        if interaction.user not in players:
            await interaction.response.send_message("أنت لست مشاركاً في هذه الجولة!", ephemeral=True)
            return

        self.stop()
        current_turn_index += 1
        await interaction.response.send_message("تم الانتقال للدور التالي...", ephemeral=False)
        await prompt_next_question(interaction.channel)

# --- 2️⃣ كلاس قائمة التصويت المنسدلة ---
class VoteSelect(discord.ui.Select):
    def __init__(self, player_list):
        options = [
            discord.SelectOption(
                label=player.display_name,
                value=str(player.id),
                description=f"التصويت ضد {player.display_name}",
                emoji="🗳️"
            ) for player in player_list
        ]
        super().__init__(placeholder="اختر الشخص الذي تظن أنه برا السالفة...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user not in players:
            await interaction.response.send_message("أنت لست مشاركاً في هذه الجولة!", ephemeral=True)
            return

        voted_id = int(self.values[0])
        voted_user = interaction.guild.get_member(voted_id)

        votes[interaction.user.id] = voted_id
        await interaction.response.send_message(f"تم تسجيل صوتك ضد **{voted_user.display_name}**! (المصوتين حتى الآن: {len(votes)}/{len(players)})", ephemeral=True)

        if len(votes) == len(players):
            await process_vote_results(interaction.channel)

class VoteView(discord.ui.View):
    def __init__(self, player_list):
        super().__init__(timeout=1000)
        self.add_item(VoteSelect(player_list))

# --- 3️⃣ كلاس قائمة تخمين الكلمة (من نفس الفئة الحالية) ---
class WordGuessSelect(discord.ui.Select):
    def __init__(self):
        category_words = WORDS_DATABASE.get(current_category, [])
        options = [
            discord.SelectOption(label=word, value=word, emoji="💡") 
            for word in category_words
        ]
        super().__init__(placeholder=f"اختر الكلمة التي تعتقد أنها من فئة {current_category}...", options=options)

    async def callback(self, interaction: discord.Interaction):
        global is_game_running
        if interaction.user != out_player:
            await interaction.response.send_message("عذراً، التخمين مخصص فقط للشخص الذي كان برا السالفة!", ephemeral=True)
            return

        guessed_word = self.values[0]
        msg = f"🎯 **نتيجة التخمين النهائي!**\nقام {out_player.mention} باختيار الكلمة: `{guessed_word}`\n\n"

        if guessed_word == secret_word:
            msg += f"🎉 **تخمين صحيح!** استطاع {out_player.mention} تخمين الكلمة السرية `{secret_word}` بنجاح وأنقذ نفسه!\n"
            msg += f"تم إضافة **200 نقطة** لـ {out_player.mention}.\n\n"
            scores[out_player] += 200
        else:
            msg += f"❌ **تخمين خاطئ!** الكلمة الصحيحة كانت: `{secret_word}`.\n"
            msg += f"تم إضافة **100 نقطة** فقط للاعبين الذين صوّتوا بشكل صحيح ضد {out_player.mention}!\n\n"
            
            # إعطاء نقاط فقط لمن صوت صح على الشخص اللي برا السالفة
            for voter_id, voted_target_id in votes.items():
                if voted_target_id == out_player.id:
                    voter_member = interaction.guild.get_member(voter_id)
                    if voter_member and voter_member in scores:
                        scores[voter_member] += 100

        msg += get_leaderboard_text()
        await interaction.response.send_message(msg)
        is_game_running = False

class WordGuessView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(WordGuessSelect())

# --- 4️⃣ دالة معالجة نتائج التصويت ---
async def process_vote_results(channel):
    global is_game_running
    vote_counts = {}
    
    for voted_id in votes.values():
        vote_counts[voted_id] = vote_counts.get(voted_id, 0) + 1

    max_votes = max(vote_counts.values())
    top_voted_ids = [player_id for player_id, count in vote_counts.items() if count == max_votes]

    # ⚖️ حالة التعادل في الأصوات
    if len(top_voted_ids) > 1:
        tied_members = [channel.guild.get_member(pid).mention for pid in top_voted_ids if channel.guild.get_member(pid)]
        members_str = " و ".join(tied_members)
        
        msg = f"⚖️ **حدث تعادل في التصويت بين:** {members_str} ({max_votes} أصوات لكل منهما)!\n\n"

        # إذا كان الشخص اللي برا السالفة واحد من المتعادلين
        if out_player.id in top_voted_ids:
            msg += f"🔍 **بما أن {out_player.mention} (اللي برا السالفة) تم انكشافه ضمن التعادل:**\n"
            msg += f"🚨 **فرصة النجاة:** يا {out_player.mention}، اختر الكلمة الصحيحة من الفئة `{current_category}` لتنقذ نفسك وتفوز بالنقاط:\n"
            msg += f"*(ملاحظة: النقاط ستذهب فقط للذين صوّتوا ضد {out_player.mention} إذا أخطأ بالتخمين)*"
            
            guess_view = WordGuessView()
            await channel.send(msg, view=guess_view)
        else:
            # إذا كان الشخص اللي برا السالفة مش موجود بالتعادل أصلاً (خدع الجميع)
            msg += f"❌ **لم يستطع أحد اكتشاف الشخص الحقيقي اللي برا السالفة!**\n"
            msg += f"🎭 الشخص الذي كان برا السالفة وخدعكم بنجاح هو: {out_player.mention}!\n"
            msg += f"الكلمة كانت: `{secret_word}`\nتم إضافة **200 نقطة** لـ {out_player.mention}.\n\n"
            
            scores[out_player] += 200
            msg += get_leaderboard_text()
            await channel.send(msg)
            is_game_running = False

    # 🎯 حالة عدم وجود تعادل (فائز صريح بأعلى أصوات)
    else:
        most_voted_id = top_voted_ids[0]
        most_voted_user = channel.guild.get_member(most_voted_id)

        msg = f"📊 **انتهى التصويت من جميع اللاعبين!**\n\nالشخص الذي حصل على أعلى الأصوات هو: **{most_voted_user.mention}**\n\n"

        if most_voted_id == out_player.id:
            msg += f"🎉 **إجابة صحيحة!** {out_player.mention} هو بالفعل الشخص الذي كان **برا السالفة**!\n"
            msg += f"🚨 **فرصة النجاة:** يا {out_player.mention}، اختر الكلمة الصحيحة من القائمة أسفله لتنقذ نفسك وتفوز بالنقاط:"
            guess_view = WordGuessView()
            await channel.send(msg, view=guess_view)
        else:
            msg += f"❌ **إجابة خاطئة!** {most_voted_user.mention} كان **جوا السالفة**!\n"
            msg += f"🎭 الشخص الذي كان برا السالفة وخدعكم بنجاح هو: {out_player.mention}!\n"
            msg += f"الكلمة كانت: `{secret_word}`\nتم إضافة **200 نقطة** لـ {out_player.mention}.\n\n"
            
            scores[out_player] += 200

            msg += get_leaderboard_text()
            await channel.send(msg)
            is_game_running = False

def get_leaderboard_text():
    sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    text = "🏆 **جدول نقاط المشاركين بعد هذه الجولة:**\n"
    for rank, (player, score) in enumerate(sorted_scores, 1):
        if player in players:
            text += f"**{rank}.** {player.display_name} ➔ `{score}` نقطة\n"
    return text

# --- 5️⃣ كلاس أزرار الانضمام والتسجيل ---
class JoinView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="انضمام للعبة 🎮", style=discord.ButtonStyle.success)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in players:
            await interaction.response.send_message("أنت مسجل بالفعل!", ephemeral=True)
        else:
            players.add(interaction.user)
            if interaction.user not in scores:
                scores[interaction.user] = 0
            await interaction.response.send_message(f"تم تسجيلك بنجاح يا {interaction.user.mention}!", ephemeral=False)

    @discord.ui.button(label="بدء الجولة 🚀", style=discord.ButtonStyle.primary)
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(players) < 3:
            await interaction.response.send_message("يجب أن يكون عدد اللاعبين 3 على الأقل لبدء اللعبة!", ephemeral=True)
            return
        
        await interaction.response.send_message("جاري توزيع الأدوار وإرسال الرسائل الخاصة... 🤫")
        self.stop()
        await start_round(interaction.channel)

# --- 6️⃣ أوامر البوت ---
@bot.command()
async def start(ctx):
    """بدء روم التسجيل للعبة"""
    global players, is_game_running
    if is_game_running:
        await ctx.send("هناك جولة شغالة حالياً! انتظر لحين انتهائها.")
        return

    players = set()
    view = JoinView()
    await ctx.send("🎲 **بدأت لعبة مين برا السالفة!**\nاضغطوا على زر الانضمام أدناه للمشاركة (الحد أدنى 3 لاعبين):", view=view)

@bot.command()
async def leaderboard(ctx):
    """عرض قائمة النقاط والترتيب الشامل"""
    if not scores:
        await ctx.send("لا يوجد نقاط مسجلة بعد.")
        return

    sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    msg = "🏆 **جدول ترتيب جميع اللاعبين:**\n"
    for rank, (player, score) in enumerate(sorted_scores, 1):
        msg += f"**{rank}.** {player.display_name} ➔ `{score}` نقطة\n"
    
    await ctx.send(msg)

@bot.event
async def on_ready():
    print(f'تم تشغيل البوت بنجاح باسم: {bot.user}')

bot.run('Missing part')
