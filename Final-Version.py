import telegram
import logging
import telegram.ext
from telegram.ext import MessageHandler, filters
from telegram.ext import CallbackQueryHandler, ConversationHandler, CallbackContext
from telegram.ext import Updater,CallbackContext,CommandHandler,MessageHandler, Application
from telegram import InlineKeyboardButton, InlineKeyboardMarkup ,Update
import pymongo
from pymongo import MongoClient
from telegram.constants import ChatAction


client = MongoClient("localhost",27017)
db = client["Inventory"]
collection = db["Stationary"]
cart_collection=db['Cart']

GET_ADDRESS = range(2)
CONFIRM_ORDER, NUMBER, GET_ADDRESS = range(3)

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
            "text": f"{option['item']} (₹{option['price']})",
            "callback_data": option['item']
        })
    return checkbox_options

start_text='''Hii!! Welcome to Stationary Shop  !!!

Introducing our telegram bot that makes shopping at our stationary store even easier.

If you are new , kindly go through the following commands :-

/Items : Displays the list of items available at the store
/Cart  : Displays items you have added in cart
/Clear : Makes your cart empty
/Total : Displays the total Amount of Cart
/Remove Item_name : Removes the specified item from cart
/Confirm_order : When you're done shopping click on this 
/partner : Displays details of delivery partner 
/Contact : Dispays the owner information

Instructions:
~ Always start using the bot with /start command so as to retrieve items in cart
~ If any item is to be added more than once,just click multiple times.
~ Kindly use /total to see the total amount before confirming the order.


'''

async def start(update: Update, context: CallbackContext):
      await context.bot.send_message(chat_id=update.effective_chat.id, text=start_text)
      chat_id = update.effective_chat.id
      filter = {"user_id": chat_id}
      result = cart_collection.find_one(filter)
      shopping_list[chat_id] = []
      if result:
        shopping_list[chat_id]= result["items"]
        print("Record retrieved for", chat_id)
    
    
async def show_list(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    cart_dict = { "user_id" : chat_id, "items" : shopping_list[chat_id]}
    cart_collection.delete_one(cart_dict)
    checkbox_options = get_checkbox_options()
    reply_markup = InlineKeyboardMarkup(build_menu(checkbox_options, n_cols=1))
    await update.message.reply_text('Please select an item to add to your Cart:', reply_markup=reply_markup)
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
    await context.bot.send_message(chat_id=query.message.chat_id, text=f'{item} added to your Cart.')
    
    
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
            await context.bot.send_message(chat_id=chat_id, text='Your Cart is empty.')
        else:
            await context.bot.send_message(chat_id=chat_id, text='\n'.join(shopping_list[chat_id]))
    else:
        await context.bot.send_message(chat_id=chat_id, text='Your Cart is empty.')

async def remove_item(update, context):
    chat_id = update.effective_chat.id
    item = context.args[0]
    cart_dict = { "user_id" : chat_id, "items" : shopping_list[chat_id]}
    cart_collection.delete_one(cart_dict)
    if chat_id in shopping_list and item in shopping_list[chat_id]:
        shopping_list[chat_id].remove(item)
        await context.bot.send_message(chat_id=chat_id, text=f'{item} removed from your Cart.')
    else:
        await context.bot.send_message(chat_id=chat_id, text=f'{item} is not in your Cart.')
    cart_dict = { "user_id" : chat_id, "items" : shopping_list[chat_id]}
    save_to_cart(cart_dict)    
 
async def clear_list(update, context):
    chat_id = update.effective_chat.id
    shopping_list[chat_id] = []
    await context.bot.send_message(chat_id=chat_id, text='Your Cart has been cleared.')
    cart_dict = { "user_id" : chat_id, "items" : shopping_list[chat_id]}
    cart_collection.delete_one(cart_dict)

async def summary(update, context):
    total_price = 0
    chat_id = update.effective_chat.id
    cart_dict = { "user_id" : chat_id, "items" : shopping_list[chat_id]}
    cart_collection.delete_one(cart_dict)
    save_to_cart(cart_dict)
    if chat_id in shopping_list:
        if not shopping_list[chat_id]:
            await context.bot.send_message(chat_id=chat_id, text='Your Cart is empty.')
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
            message += f"{item}: ₹{price}\n"
        message += f"Total price: ₹{total_price}"
        await context.bot.send_message(chat_id=chat_id, text=message)
    else:
        await context.bot.send_message(chat_id=chat_id, text='Your Cart is empty.')
    
         
async def contact(update, context: CallbackContext):
    owner_phone_number = "+917018070040"
    owner_email = "vishalakshik02@gmail.com"
    owner_address="55/4 Knott Street,Patiala,Punjab"
    message = f"Here are the contact details for the owner of the store:\n\nPhone number: {owner_phone_number}\nEmail: {owner_email}\nAddress: {owner_address}"
    await update.message.reply_text(message)


async def start_confirm_order(update, context: CallbackContext) -> int:
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="Would you like to confirm your order? (Yes/No)")
    return CONFIRM_ORDER



async def process_response(update:Application, context: CallbackContext) -> int:
    text = update.message.text.lower()
    if text == 'yes':
        await update.message.reply_text("Great! Provide some information so as we can proceed with the order.")
        await update.message.reply_text("Kindly click on  /location to provide shipping address")

        
    elif text == 'no':
        await update.message.reply_text("Unfortunately, your order has been cancelled.")
    else:
        await update.message.reply_text("I'm sorry, I didn't understand. Please type 'Yes' or 'No' to confirm or cancel your order.")
        return CONFIRM_ORDER
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Order cancelled!")
    return ConversationHandler.END

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('confirm_order', start_confirm_order)],
    states={
        CONFIRM_ORDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_response)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)



async def delivery_partner(update, context):
    chat_id = update.effective_chat.id
    partner_collection = db['Partners']
    delivery_partner = partner_collection.aggregate([{ '$sample': { 'size': 1 } }]).next()
    partner_collection.update_one({'user_id': chat_id}, {'$set': {'delivery_partner': delivery_partner}})

    message = "Partner Details:\n\n"
    name = delivery_partner['Name']
    phone = delivery_partner['contact']
    message += f"Name:{name}\nPhone: {phone}\n"
    await context.bot.send_message(chat_id=chat_id, text=message)



async def location(update, context):
     chat_id = update.effective_chat.id
     context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
     await context.bot.send_message(chat_id=chat_id, text="Please enter your complete address")
     return GET_ADDRESS

Partner='''For checking delivery partner details you can use /Partner '''
QQ='''Thank you! Your Order has been confirmed 
      Delivery partner will be assigned shortly.'''


async def contact_number(update, context):
     chat_id = update.effective_chat.id
     phone = update.message.text
     orders_collection = db["Orders"]
     context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
     orders_collection.update_one({'user_id': chat_id}, {'$set': {'phone': phone}})
     cart_dict = { "user_id": chat_id, "items": shopping_list[chat_id]}
     orders_collection.update_one({'user_id': chat_id}, {'$set': {'Items': cart_dict['items']}})
     filter = {"user_id": chat_id}
     result = cart_collection.find_one(filter)
     shopping_list[chat_id] = []
     cart_dict = { "user_id" : chat_id, "items" : shopping_list[chat_id]}
     cart_collection.delete_one(cart_dict)
     shopping_list[chat_id] = []
     await context.bot.send_message(chat_id = update.effective_chat.id, text=QQ)
     await context.bot.send_message(chat_id = update.effective_chat.id, text=Partner)
     return ConversationHandler.END

async def handle_address(update, context):
    chat_id = update.effective_chat.id
    address = update.message.text
    orders_collection = db["Orders"]

    if orders_collection.find_one({'user_id': chat_id}):
       orders_collection.delete_one({'user_id': chat_id})
    
    
    orders_collection.insert_one({'user_id': chat_id, 'address': address})
    await context.bot.send_message(chat_id = update.effective_chat.id, text="Thank you!")
    await context.bot.send_message(chat_id = update.effective_chat.id, text="Kindly provide you phone number")
    return NUMBER


def cancel(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    #context.user_data.clear()
    update.message.reply_text('Current operation cancelled. What would you like to do next?')
    return ConversationHandler.END


conv_handler2 = ConversationHandler(
    entry_points=[CommandHandler('location', location)],
    states={
        GET_ADDRESS: [ MessageHandler(filters.TEXT & ~filters.COMMAND, handle_address)],
        NUMBER : [MessageHandler(filters.TEXT & ~filters.COMMAND, contact_number) ]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

def save_to_cart(x):
    cart_collection.insert_one(x)
    print("record inserted")


def error(update, context):
    logging.error(f'Update {update} caused error {context.error}')


def main():   
    app = Application.builder().token(TOKEN).build()
    app.add_handler(telegram.ext.CommandHandler('Start',start))
    app.add_handler(telegram.ext.CommandHandler('Items',show_list))
    app.add_handler(telegram.ext.CommandHandler('Total',summary))
    app.add_handler(CallbackQueryHandler(checkbox_selection))
    app.add_handler(telegram.ext.CommandHandler('Cart', list_items))
    app.add_handler(telegram.ext.CommandHandler('Remove', remove_item))
    app.add_handler(telegram.ext.CommandHandler('Clear', clear_list))
    app.add_handler(telegram.ext.CommandHandler('Contact', contact))
    app.add_handler(telegram.ext.CommandHandler('Partner',delivery_partner))
    app.add_handler(telegram.ext.CommandHandler('Cancel',cancel))
    app.add_handler(conv_handler)
    app.add_handler(conv_handler2)
    app.add_error_handler(error)
    app.run_polling()
    app.idle()

if __name__ == '__main__':
    main()
