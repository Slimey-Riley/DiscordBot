'''
Discord bot to handle multiple functionalities for books for users. Including reading lists and finding books!

Author: Riley
'''


import discord
from dotenv import load_dotenv
import os
import json
import requests
import sqlite3
import asyncio
from sqlite3 import Error

class Loop_Handler:
  async def add_emojis(self, reply, i, dict, embeds, message):
    emojis = ['⬅️', '➡️']

    def check(reaction, user):
        return user == message.author and str(reaction.emoji) in emojis and reaction.message == reply
    
    for emoji in emojis:
      await reply.add_reaction(emoji)
    try:
      emojiWait, user = await bot.wait_for('reaction_add', check=check, timeout=60.0)
    except asyncio.TimeoutError:
      print('timeout')

    else:
      if emojiWait.emoji == emojis[0]: 
        i -= 1
        if i == -1: i = len(dict) - 1
        await Loop_Handler.edit_book(self, reply, i, dict, embeds, message)
      if emojiWait.emoji == emojis[1]:  
        i+=1
        if i == len(dict): i = 0
        await Loop_Handler.edit_book(self, reply, i, dict, embeds, message)
  
  #edits search reply to new reply
  async def edit_book(self, reply, i, dict, embeds, message):
    await reply.clear_reactions()
    reply = await reply.edit(embed=embeds[i])
    await Loop_Handler.add_emojis(self, reply, i, dict, embeds, message)



class List_Handler:

  def create_book(self, conn, book, table):
    """
      Create a new book into the user's table
      :param conn:
      :param book:
      :param table:
      :return: book id
    """
    sql = ''' INSERT or IGNORE INTO ''' + table + '''(name,author,description,isbn10,isbn13,image)
                VALUES(?,?,?,?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, book)
    conn.commit()
    return cur.lastrowid

  def delete_book(self, conn, name, table):
    """
      Delete a book from users table by name
      :param conn:  Connection to the SQLite database
      :param name: name or isbn of book
      :return:
      """
    sql = 'DELETE FROM ' + table + ' WHERE name=?'
    cur = conn.cursor()
    cur.execute(sql, (name, ))
    if cur.rowcount <= 0:
      return 0
    if cur.rowcount > 0:
      conn.commit()
      return 1


class Book_Handler:

  def search_books(self, query):
    """
      Searches for books from user query using 
      GoogleBooks Api
  
      Returns data in dictionary format
    """

    #Get all the book data in json format from the items dict
    books = requests.get("https://www.googleapis.com/books/v1/volumes?q=" +
                         query + "&key=" + BOOKS_KEY).json()['items']

    #set up our own dictionary for storing data
    book_dict = {}

    #store data in dictionary
    i = 0
    for domain in books:
      title = domain.get('volumeInfo').get('title', 'Not Found')
      author = domain.get('volumeInfo').get('authors', 'Not Found')
      rating = domain.get('volumeInfo').get('averageRating', 'Not Found')
      description = domain.get('volumeInfo').get('description', 'Not Found')
      try:
        isbn10 = domain.get('volumeInfo').get('industryIdentifiers')[0].get(
          'identifier')
      except:
        isbn10 = "0"
      try:
        isbn13 = domain.get('volumeInfo').get('industryIdentifiers')[1].get(
          'identifier')
      except:
        isbn13 = "0"
      try:
        image = domain.get('volumeInfo').get('imageLinks', 'Not Found').get(
          'thumbnail', 'Not Found')
      except:
        image = ''
      url = domain.get('volumeInfo').get('previewLink', 'Not Found')
      book_dict[i] = {
        'title': title,
        'author': author,
        'rating': rating,
        'description': description,
        'image': image,
        'url': url,
        'isbn10': isbn10,
        'isbn13': isbn13
      }
      i += 1

    #return dictionary
    return book_dict


class Database_Handler:

  def create_connection(self, db_file):
    """ 
      Create a database connection to a SQLite database 
    """
    conn = None
    try:
      conn = sqlite3.connect(db_file)
    except Error as e:
      print(e)
    return conn

  def create_table(self, conn, create_table_sql):
    """ 
      Creates a table
      :param conn: Connection
      :param create_table_sql: CREATE TABLE statement
    """
    try:
      c = conn.cursor()
      c.execute(create_table_sql)
    except Error as e:
      print(e)


#set discord intents
intents = discord.Intents.default()
intents.message_content = True

#setup bot connection
bot = discord.Client(intents=intents)

#create handlers
list_handler = List_Handler()
database_handler = Database_Handler()
book_handler = Book_Handler()

#connect to db
conn = database_handler.create_connection('database.db')
cur = conn.cursor()

#get api keys from environment file
load_dotenv('token.env')
DISCORD_KEY = os.getenv("DISCORD_KEY")
BOOKS_KEY = os.getenv("BOOKS_KEY")


@bot.event
async def on_ready():
  #when bot is ready
  print(f'We have logged in as {bot.user}')


@bot.event
async def on_message(message):
  #ignore ourselves
  if message.author == bot.user:
    return

  msg = message.content

  #bot command
  if msg.startswith('$lib'):
    cmd = msg.split('$lib ', 1)[1]


    if 'help' in cmd:
      embed = discord.Embed(title="Help", color=0xFF5733)
      embed.add_field(name="Search", value="Searches for a book with query name, you can look for a specific book or themes and genres.\nCommand - $lib search (query)", inline=False)
      embed.add_field(name="Add", value="Adds a book to your list, leave the listname blank to add to base reading list. Will create a list with listname if not already created. listname must have no spaces and no special characters. \nCommand - $lib (listname) add (query)", inline=False)
      embed.add_field(name="Remove", value="Removes a book from your list, leave the listname blank to remove from reading list.\nCommand - $lib (listname) remove (query)", inline=False)
      embed.add_field(name="Show", value="shows your specified list, leave listname blank to show reading list.\nCommand - $lib show (listname)", inline=False)

      await message.channel.send(embed=embed)
    
    if 'search' in cmd:
      #search for book
      query = cmd.split('search ', 1)[1]
      book_dict = book_handler.search_books(query)
      embeds = []
      for book in book_dict.values():
        embed = discord.Embed(title=book['title'],
                              url=book['url'],
                              description=book['description'],
                              color=0xFF5733)
        embed.set_thumbnail(url=book['image'])
        embed.add_field(name='Author', value=book['author'][0], inline=True)
        embed.add_field(name='Rating', value=book['rating'], inline=True)
        embeds.append(embed)
      
      #adds emojis and emoji listener to scroll through search results
      
      reply = await message.channel.send(embed=embeds[0])
      loop_handler = Loop_Handler()
      await loop_handler.add_emojis(reply, 1, book_dict, embeds, message)

    if 'add' in cmd:
      #add book to database
      try:
        table_prefix = cmd.split('add', 1)[0]
        query = ''
        if (table_prefix == ''):
          table_prefix = 'rl'
          query = cmd.split('add ', 1)[1]
        else:
          query = cmd.split(' add ', 1)[1]
          table_prefix = cmd.split(' add ', 1)[0]
        
        table_name = table_prefix + str(message.author.id)
        book_dict = book_handler.search_books(query)
        sql_create_user_table = """CREATE TABLE IF NOT EXISTS """ + table_name + """ (
                            name text NOT NULL UNIQUE,
                            author text, 
                            description text,
                            isbn10 text,
                            isbn13 text,
                            image text
                        ); """
        # create tables
        if conn is not None:
          # create table
          database_handler.create_table(conn, sql_create_user_table)
        else:
          "Error! cannot create the database connection."
        book = (str(book_dict[0]['title']), str(book_dict[0]['author'][0]),
                str(book_dict[0]['description']).replace("'", '"'),
                str(book_dict[0]['isbn10']), str(book_dict[0]['isbn13']),
                str(book_dict[0]['image']))
        list_handler.create_book(conn, book, table_name)
        if (table_prefix == 'rl'):
          await message.channel.send("Added " + str(book_dict[0]['title']) +
                                     " to your reading list")
        else:
          await message.channel.send("Added " + str(book_dict[0]['title']) +
                                     " to " + table_prefix)
      except:
        await message.channel.send("Could not create list, see ($lib help) for more info")

    
    if 'remove' in cmd:
      #remove book from database
      try:
        table_prefix = cmd.split('remove', 1)[0]
        query = ''
        if (table_prefix == ''):
          table_prefix = 'rl'
          query = cmd.split('remove ', 1)[1]
        else:
          query = cmd.split(' remove ', 1)[1]
          table_prefix = cmd.split(' remove ', 1)[0]
        table_name = table_prefix + str(message.author.id)
        if (list_handler.delete_book(conn, query, table_name) == 1):
          if (table_prefix == 'rl'):
            await message.channel.send("Removed " + query +
                                       " from your reading list")
          else:
            await message.channel.send("Removed " + query + " from " +
                                       table_prefix)
        else:
          if (table_prefix == 'rl'):
            await message.channel.send("Could not find " + query +
                                       " in your reading list")
          else:
            await message.channel.send("Could not find " + query + " in " +
                                       table_prefix)
      except:
        await message.channel.send("Could not find list")

    
    if 'show' in cmd:
      #shows lists data
      try:
        table_prefix = cmd.split('show', 1)[1]
        query = ''
        if (table_prefix == ''):
          table_prefix = 'rl'
        else:
          table_prefix = cmd.split('show ', 1)[1]
        table_name = table_prefix+str(message.author.id)
        sql_query = """SELECT name, description, image, author FROM """ + table_name
        cur.execute(sql_query)
        for row in cur.fetchall():
          embed = discord.Embed(title=row[0], description=row[1], color=0xFF5733)
          embed.set_thumbnail(url=row[2])
          embed.add_field(name='Author', value=row[3], inline=True)
          await message.channel.send(embed=embed)
      except:
        await message.channel.send("Could not find list")


bot.run(DISCORD_KEY)