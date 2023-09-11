#import telegram
import logging
import telegram.ext
from telegram.ext import filters,Updater,CallbackContext,CommandHandler,MessageHandler, Application,CallbackQueryHandler,ConversationHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup ,Update
import pymongo
from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("localhost",27017)
db = client["Inventory"]
collection = db["Stationary"]
cart_collection = db['Cart']


try:
    client.admin.command('ismaster')
    print("MongoDB connected")
except pymongo.errors.ConnectionFailure as e:
    print("MongoDB connection failed: %s" % e)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
TOKEN="5914668156:AAF01FAUZyjJGnTxMzNVaYvahlchLhdlM8Y"
shopping_list = {}
print(shopping_list)

GET_LOCATION, GET_ADDRESS = range(2)
CONFIRM_ORDER, GET_LOCATION, GET_ADDRESS = range(3)

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
      chat_id = update.effective_chat.id
      shopping_list[chat_id] = []
      if 'shopping_list' not in context.chat_data:
       context.chat_data['shopping_list'] = {}
    #    store_cart(chat_id, context.chat_data['shopping_list'].get(chat_id, []))
      #store_cart(chat_id, shopping_list[chat_id])
      retrieve_cart(chat_id)
   
async def show_list(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    checkbox_options = get_checkbox_options()
    reply_markup = InlineKeyboardMarkup(build_menu(checkbox_options, n_cols=1))
    await update.message.reply_text('Please select an item to add to your shopping cart:', reply_markup=reply_markup)
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
    await context.bot.send_message(chat_id=query.message.chat_id, text=f'{item} added to your shopping cart.')
    store_cart(chat_id, shopping_list[chat_id])
    # retrieve_cart(chat_id)
 #   query.edit_message_text(text=f"You selected: {item}. Your shopping list now includes: {', '.join(shopping_list[chat_id])}")

def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu

async def cart(update, context):
    chat_id = update.effective_chat.id
    # store_cart(chat_id, shopping_list[chat_id])
    # retrieve_cart(chat_id)
    if chat_id not in shopping_list:
       shopping_list[chat_id] = []
    # store_cart(chat_id, shopping_list[chat_id])
    # retrieve_cart(chat_id)
    if chat_id in shopping_list:
        if not shopping_list[chat_id]:
            await context.bot.send_message(chat_id=chat_id, text='Your shopping cart is empty.')
        else:
            await context.bot.send_message(chat_id=chat_id, text='\n'.join(shopping_list[chat_id]))
    else:
        await context.bot.send_message(chat_id=chat_id, text='Your shopping cart is empty.')

        
        

async def remove_item(update, context):
    chat_id = update.effective_chat.id
    item = context.args[0]
    if chat_id in shopping_list and item in shopping_list[chat_id]:
        shopping_list[chat_id].remove(item)
        await context.bot.send_message(chat_id=chat_id, text=f'{item} removed from your shopping cart.')
    else:
        await context.bot.send_message(chat_id=chat_id, text=f'{item} is not in your shopping cart.')
    
    store_cart(chat_id, shopping_list[chat_id])
    retrieve_cart(chat_id)    
 
async def clear_list(update, context):
    chat_id = update.effective_chat.id
    shopping_list[chat_id] = []
    store_cart(chat_id, shopping_list[chat_id])
    retrieve_cart(chat_id)    
    await context.bot.send_message(chat_id=chat_id, text='Your shopping cart has been cleared.')

async def summary(update, context):
    total_price = 0
    chat_id = update.effective_chat.id
    if chat_id in shopping_list:
        if not shopping_list[chat_id]:
            await context.bot.send_message(chat_id=chat_id, text='Your shopping cart is empty.')
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
        await context.bot.send_message(chat_id=chat_id, text='Your shopping cart is empty.')


# def location(update, context):
#     context.bot.send_message(chat_id=update.message.chat_id, text="Please share your location", reply_markup=telegram.ReplyKeyboardRemove())
#     return GET_LOCATION

# def handle_location(update, context):
#     location = update.message.location
#     latitude = location.latitude
#     longitude = location.longitude
#     context.user_data['location'] = {'latitude': latitude, 'longitude': longitude}
#     context.bot.send_message(chat_id=update.message.chat_id, text="Please enter your complete address")
#     return GET_ADDRESS

# def handle_address(update, context):
#     address = update.message.text
#     client = pymongo.MongoClient("mongodb://localhost:27017/")
#     db = client["inventory"]
#     orders_collection = db["Orders"]
#     orders_collection.insert_one({'location': context.user_data['location'], 'address': address})
#     context.bot.send_message(chat_id=update.message.chat_id, text="Thank you for your order!")
#     return ConversationHandler.END

# def cancel(update, context):
#     # Send a message indicating that the conversation has been canceled
#     context.bot.send_message(chat_id=update.message.chat_id, text="Order canceled")
#     return ConversationHandler.END


# conv_handler = ConversationHandler(
#     entry_points=[CommandHandler('order', location)],
#     states={
#         GET_LOCATION: [MessageHandler(filters.location, handle_location)],
#         GET_ADDRESS: [MessageHandler(filters.text, handle_address)]
#     },
#     fallbacks=[CommandHandler('cancel', cancel)]
# )
   
# def confirm_order(update, context):
#     keyboard = [[InlineKeyboardButton("Yes", callback_data='confirm'),
#                  InlineKeyboardButton("No", callback_data='cancel')]]
#     reply_markup = InlineKeyboardMarkup(keyboard)
#     context.bot.send_message(chat_id=update.message.chat_id, text="Do you confirm your order?", reply_markup=reply_markup)
#     return CONFIRM_ORDER

# def handle_confirmation(update, context):
#     query = update.callback_query
#     if query.data == 'confirm':
#         query.edit_message_text(text="Thank you for confirming your order!")
#         clear_list
#         return GET_LOCATION
#     else:
#         query.edit_message_text(text="Order cancelled.")
#         return ConversationHandler.END   


# def cancel(update, context):
#     context.bot.send_message(chat_id=update.message.chat_id, text="Order cancelled")
#     return ConversationHandler.END

# conv_handler = ConversationHandler(
#     entry_points=[CommandHandler('order', confirm_order)],
#     states={
#         CONFIRM_ORDER: [CallbackQueryHandler(handle_confirmation)],
#         GET_LOCATION: [MessageHandler( filters.location , handle_location)],
#         GET_ADDRESS: [MessageHandler( filters.text , handle_address)]
#     },
#     fallbacks=[CommandHandler('cancel', cancel)]
# )




# def store_cart(user_id, items):
#     cart = {
#         'user_id': user_id,
#         'items': items
#     }
#     cart_collection.replace_one({'user_id': user_id}, cart, upsert=True)



def store_cart(chat_id, item):
    if chat_id not in cart_collection:
        cart = {
         'user_id': chat_id,
         'items': []
        }
        cart_collection.insert_one(cart)
    else: 
        cart_collection.find_one(chat_id)
        cart_collection['items'].append(item)

    
    # if result.inserted_id:
    #     return
    # else:
    #     filter = {'user_id': chat_id}
    #     cart_collection.replace_one(filter, cart)


def retrieve_cart(chat_id):
    filter = {'user_id': chat_id}
    result = cart_collection.find_one(filter)
    if result:
        shopping_list[chat_id].append(result)
        return shopping_list
    else:
        return []



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
    app.add_handler(telegram.ext.CommandHandler('Cart', cart))
    app.add_handler(telegram.ext.CommandHandler('Remove', remove_item))
    app.add_handler(telegram.ext.CommandHandler('Clear', clear_list))
    app.add_handler(telegram.ext.CommandHandler('Contact', contact))
    # app.add_handler(telegram.ext.CommandHandler('confirm', confirm_order))
    # app.add_handler(conv_handler)
    app.add_error_handler(error)
    app.run_polling()
    app.idle()
if __name__ == '__main__':
    main()
