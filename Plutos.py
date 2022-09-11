import telebot
import pypyodbc
from telebot import types
import json
from datetime import date
import requests

todos = json.loads(requests.get('https://belarusbank.by/api/kursExchange').text)
todo=todos[0]

connection = pypyodbc.connect('Driver={SQL Server};'
                              'Server=LAPTOP-IABV41BR\SQLEXPRESS;'
                              'Database=VTB;')
bot = telebot.TeleBot('5369533162:AAENzKxtRR34IwQSDVGLC3A3ACFUwqSrBDw')

cursor = connection.cursor()

mySQLQuery = ("""
    SELECT RoleCode, Id 
    FROM dbo.Role
    """)
cursor.execute(mySQLQuery)
results = cursor.fetchall()

isQuestion = False
openQuestionId = -1

def IsUserExist(telegramId):
    sql = "SELECT * FROM Users WHERE TelegramId = '{}'".format(telegramId);
    cursor.execute(sql)
    results = cursor.fetchall()
    return len(results) != 0;

def SendMessage(chatId, message):
    bot.send_message(
        chatId,
        message,
        reply_markup=keyboard()
    )

def Init(message):
    SendMessage(message.chat.id, 'Выберите интересующую вас тему')

def Login(message):
    id = message.from_user.id
    isExist = IsUserExist(id)
    if(not isExist):
        keyboard1 = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        reg_button = types.KeyboardButton(text="Отправить номер телефона", request_contact=True)
        keyboard1.add(reg_button)
        bot.send_message(message.chat.id, 'Здраствуйте, Оставьте ваш контактный номер чтобы наш менеджер смог связаться с вами.', reply_markup=keyboard1)
    else:
        Init(message)

def register(message):
    sql = ("""
    INSERT INTO Users([Name], [PhoneNumber], [IsActivated], [TelegramId]) VALUES('{}','{}','{}','{}')
    """.format(message.contact.first_name, message.contact.phone_number, 1, message.contact.user_id))
    resp = cursor.execute(sql)
    connection.commit()
    Login(message)

def GetComment(chatId):
    SendMessage(chatId, "Введите вопрос")

def PushQuestion(text):
    global openQuestionId
    cursor.execute("""UPDATE UserQuestion SET Text = '{}' WHERE Id = '{}'""".format(text, openQuestionId))
    connection.commit()
    openQuestionId = -1
    return True

@bot.message_handler(commands=['start'])
def send_welcome(message):
    Login(message)

@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    register(message)

@bot.callback_query_handler(func=lambda message:True)
def send_anytext(message):

    if message.data == 'wallet_return':
        bot.send_message(message.from_user.id,
                         '''\n\n✅ Вы в главном меню\n\n''',
                         parse_mode='HTML',
                         reply_markup=keyboard())

    if "ThemeId" in message.data:
        ThID= int(message.data.split(' ')[1])
        # подготовленный запрос, защита от sql-иньекций
        com = bot.send_message(message.from_user.id, 'Введите сообщение')
        global isQuestion
        isQuestion = True;
        resp = cursor.execute("""insert into UserQuestion ([TelegramUserId], [ThemeId]) values('{}','{}')""".format(message.from_user.id, ThID))
        connection.commit()
        cursor.execute("SELECT MAX([UserQuestion].Id) FROM [UserQuestion]")
        global openQuestionId
        openQuestionId = cursor.fetchone()[0]

    if "QuestionId" in message.data:
        NowID = int(message.data.split(' ')[1])

        SQLQ=(""" 
            select p.Name, p.Id
            from Questions q
            join QuestionQuestion qq on q.Id = qq.QuestionFk
            join Questions p on qq.NextQuestionFk = p.Id
            where q.Id = {}
            """.format(NowID))
        cursor.execute(SQLQ)
        LinkQuestions = cursor.fetchall()

        if LinkQuestions == []:
            SQLQ1 = (""" 
                        select t.Text, t.Id
                        from Questions q
                        join QuestionTheme qq on q.Id = qq.QuestionFk
                        join Themes t on qq.ThemeFk = t.Id
                        where q.Id = {}
                        """.format(NowID))

            cursor.execute(SQLQ1)
            LinkTheme = cursor.fetchall()
            textt= LinkTheme[0][0]

            bot.send_message(message.from_user.id,
                             textt, parse_mode='HTML',
                             reply_markup=themebal(LinkTheme))
            return

        text = 'Выберите тему ⬇ \n\n'

        bot.send_message(message.from_user.id,
                         text,
                         parse_mode='HTML',
                         reply_markup=balance(LinkQuestions))

    if "get-" in message.data:
        today = date.today()
        if message.message:
            if message.data == 'get-USD':
                bot.send_message(message.message.chat.id,
                                 "USD\nПокупка -> " + todo['USD_in'] + "\nПродажа -> " + todo['USD_out'] + "\n" + str(
                                     today))
            elif message.data == 'get-EUR':
                bot.send_message(message.message.chat.id,
                                 "EUR\nПокупка -> " + todo['EUR_in'] + "\nПродажа -> " + todo['EUR_out'])
            elif message.data == 'get-RUB':
                bot.send_message(message.message.chat.id,
                                 "RUS (100)\nПокупка -> " + todo['RUB_in'] + "\nПродажа -> " + todo['RUB_out'])
            elif message.data == 'get-UAH':
                bot.send_message(message.message.chat.id,
                                 "UAH (100)\nПокупка -> " + todo['UAH_in'] + "\nПродажа -> " + todo['UAH_out'])

def themebal(LinkTheme):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text='Не помогло? Оставить запрос в поддержку?', callback_data="ThemeId " + str(LinkTheme[0][1])))
    markup.add(types.InlineKeyboardButton(text='⬅ Вернуться в главное меню', callback_data="wallet_return"))
    return markup

def balance (LinkQuestions):
    markup = types.InlineKeyboardMarkup()
    for row in LinkQuestions:
        markup.add(types.InlineKeyboardButton(text=str(row[0]), callback_data="QuestionId " + str(row[1])))
    markup.add(types.InlineKeyboardButton(text='⬅ Вернуться в главное меню', callback_data="wallet_return"))
    return markup

SqlQuestions = ("""
                SELECT Name, Id
                FROM dbo.Questions
                WHERE Id >=30 AND Id <=33
                """)
cursor.execute(SqlQuestions)
FirstQuestions = cursor.fetchall()

@bot.message_handler(commands=['exchange'])
def exchange_command(message):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton('USD', callback_data='get-USD'),
        telebot.types.InlineKeyboardButton('UAH', callback_data='get-UAH')
    )
    keyboard.row(
        telebot.types.InlineKeyboardButton('EUR', callback_data='get-EUR'),
        telebot.types.InlineKeyboardButton('RUB', callback_data='get-RUB')
    )

    bot.send_message(message.chat.id, 'Курсы валют к рублю:',reply_markup=keyboard)

@bot.message_handler(content_types=["text"])
def send_anytext(message):
    if(not IsUserExist(message.from_user.id)):
        bot.send_message(message.chat.id, "Без регистрации возможности ограничены(")
        Login(message)
        return

    global isQuestion
    if(isQuestion):
        if(PushQuestion(message.text)):
            SendMessage(message.chat.id, '''\n\n✅ Вопрос отправлен в call-центр\n\n''')
            isQuestion = False
        return

    cursor.execute("SELECT * FROM Role Where RoleCode = '{}'".format(message.text))
    rows = cursor.fetchone()
    if(rows == None):
        SendMessage(message.chat.id, "Упс, этого я незнаю!")
        return

    roleId = rows[0];
    cursor.execute("SELECT * FROM [QuestionRole] INNER JOIN [Questions] on [Questions].Id = [QuestionFk] WHERE [RoleFk] = '{}'".format(roleId))
    questions = cursor.fetchall()

    text = 'Выберите тему ⬇ \n\n'
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=ShowQuestion(questions))


def ShowQuestion(questions):
    markup = types.InlineKeyboardMarkup()
    for row in questions:
        markup.add(types.InlineKeyboardButton(text = str(row[3]), callback_data= "QuestionId "+str(row[2])))
    markup.add(types.InlineKeyboardButton(text='⬅ Вернуться в главное меню', callback_data="wallet_return"))
    return markup

def keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=len(results))

    i =0
    Array= []
    for row in results:
        temp = types.KeyboardButton(str(row[0]))
        Array.append(temp)
    for k in Array:
        markup.add(k)
    return markup


bot.polling(none_stop=True)
connection.close()