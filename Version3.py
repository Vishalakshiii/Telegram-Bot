#import telegram
import logging
import telegram.ext
from telegram.ext import Updater,CallbackContext,CommandHandler,MessageHandler, Application,CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup ,Update
import pymongo
from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("localhost",27017)
db = client["Inventory"]
collection = db["Stationary"]
try:
    client.admin.command('ismaster')
    print("MongoDB connected")
except pymongo.errors.ConnectionFailure as e:
    print("MongoDB connection failed: %s" % e)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
TOKEN="5914668156:AAF01FAUZyjJGnTxMzNVaYvahlchLhdlM8Y"
shopping_list = {}

def get_checkbox_options():
    options = collection.find()
    checkbox_options = []
    for option in options:
        checkbox_options.append({
            "text": f"{option['item']} (${option['price']})",
            "callback_data": option['item']
        })
    return checkbox_options

start_text='''Hii!! Welcome to Visha Stationary Shop  !!!
Introducing our telegram bot that makes shopping at our stationary store even easier.

If you are new , kindly go through the following commands :-

/Items : Displays the list of items available at the store
/Cart  : Displays items you have added in cart
/Clear : Makes your cart empty
/Total : Displays the total Amount of Cart
/Remove Item_name : Removes the specified item from cart
/Contact : Dispays the owner information
'''

async def start(update: Update, context: CallbackContext):
      await context.bot.send_message(chat_id=update.effective_chat.id, text=start_text)

# async def start(update: Update, context: CallbackContext):
#       await context.bot.send_message(chat_id=update.effective_chat.id, text='Hi! Welcome to the inventory shopping bot. Use the /show command to see inventory.')

async def show_list(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    checkbox_options = get_checkbox_options()
    reply_markup = InlineKeyboardMarkup(build_menu(checkbox_options, n_cols=1))
    await update.message.reply_text('Please select an item to add to your shopping list:', reply_markup=reply_markup)
    if chat_id not in shopping_list:
        shopping_list[chat_id] = []

async def checkbox_selection(update, context):
    query = update.callback_query
    query.answer()
    item = query.data
    chat_id = query.message.chat_id
    if chat_id not in shopping_list:
        shopping_list[chat_id] = []
    shopping_list[chat_id].append(item)
    await context.bot.send_message(chat_id=query.message.chat_id, text=f'{item} added to your shopping list.')
 #   query.edit_message_text(text=f"You selected: {item}. Your shopping list now includes: {', '.join(shopping_list[chat_id])}")

def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu

async def list_items(update, context):
    chat_id = update.effective_chat.id
    if chat_id in shopping_list:
        if not shopping_list[chat_id]:
            await context.bot.send_message(chat_id=chat_id, text='Your shopping list is empty.')
        else:
            await context.bot.send_message(chat_id=chat_id, text='\n'.join(shopping_list[chat_id]))
    else:
        await context.bot.send_message(chat_id=chat_id, text='Your shopping list is empty.')

async def remove_item(update, context):
    chat_id = update.effective_chat.id
    item = context.args[0]
    if chat_id in shopping_list and item in shopping_list[chat_id]:
        shopping_list[chat_id].remove(item)
        await context.bot.send_message(chat_id=chat_id, text=f'{item} removed from your shopping list.')
    else:
        await context.bot.send_message(chat_id=chat_id, text=f'{item} is not in your shopping list.')
 
async def clear_list(update, context):
    chat_id = update.effective_chat.id
    shopping_list[chat_id] = []
    await context.bot.send_message(chat_id=chat_id, text='Your shopping list has been cleared.')

async def summary(update, context):
    total_price = 0
    chat_id = update.effective_chat.id
    if chat_id in shopping_list:
        if not shopping_list[chat_id]:
            await context.bot.send_message(chat_id=chat_id, text='Your shopping list is empty.')
            return
        items = []
        for item in shopping_list[chat_id]:
            result = collection.find_one({"item": item})
            if result:
                price = result['price']
                total_price += price
                items.append((item, price))
            else:
                await context.bot.send_message(chat_id=chat_id, text=f"{item} is not available in the store.")
        message = ""
        for item, price in items:
            message += f"{item}: ${price}\n"
        message += f"Total price: ${total_price}"
        await context.bot.send_message(chat_id=chat_id, text=message)
    else:
        await context.bot.send_message(chat_id=chat_id, text='Your shopping list is empty.')
       
#₹   
async def contact(update: Update, context: CallbackContext):
    owner_phone_number = "+917018070040"
    owner_email = "vishalakshik02@gmail.com"
    owner_address="55/4 Knott Street,Patiala,Punjab"
    message = f"Here are the contact details for the owner of the store:\n\nPhone number: {owner_phone_number}\nEmail: {owner_email}\nAddress: {owner_address}"
    await update.message.reply_text(message)

def error(update, context):
    logging.error(f'Update {update} caused error {context.error}')


def main():   
    app = Application.builder().token(TOKEN).build()
    app.add_handler(telegram.ext.CommandHandler('Start',start))
    app.add_handler(telegram.ext.CommandHandler('Items',show_list))
    app.add_handler(telegram.ext.CommandHandler('Total',summary))
    app.add_handler(CallbackQueryHandler(checkbox_selection))
    #app.add_handler(telegram.ext.CommandHandler('add', add_item))
    app.add_handler(telegram.ext.CommandHandler('Cart', list_items))
    app.add_handler(telegram.ext.CommandHandler('Remove', remove_item))
    app.add_handler(telegram.ext.CommandHandler('Clear', clear_list))
    app.add_handler(telegram.ext.CommandHandler('Contact', contact))
    app.add_error_handler(error)
    app.run_polling()
    app.idle()
if __name__ == '__main__':
    main()
