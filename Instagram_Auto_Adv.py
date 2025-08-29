import os
import json
import random
import time
import requests
import re
import subprocess
import logging
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    ContextTypes, 
    ConversationHandler,
    filters
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('telegram_bot.log', maxBytes=10485760, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TelegramSocialBot')

# Conversation states
NICHE_SELECTION, MAIN_MENU, UPLOAD_CONTENT, YOUTUBE_PROCESSING = range(4)

# Niche options with emojis
NICHES = {
    'fitness': '💪 Fitness & Health',
    'tech': '📱 Technology & Gadgets',
    'business': '💼 Business & Entrepreneurship',
    'travel': '✈️ Travel & Adventure',
    'food': '🍔 Food & Cooking',
    'fashion': '👗 Fashion & Beauty',
    'motivation': '🔥 Motivation & Self-Improvement',
    'education': '🎓 Education & Learning',
    'entertainment': '🎬 Entertainment & Movies',
    'gaming': '🎮 Gaming & Esports'
}

class TelegramSocialBot:
    def __init__(self, token):
        self.token = token
        self.application = Application.builder().token(token).build()
        self.user_data = {}
        self.load_user_data()
        
        # Add conversation handler with niche selection
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                NICHE_SELECTION: [
                    MessageHandler(filters.Regex(f'^({"|".join(NICHES.keys())})$'), self.niche_selected),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.invalid_niche)
                ],
                MAIN_MENU: [
                    MessageHandler(filters.Regex('^📤 Upload Content$'), self.upload_content),
                    MessageHandler(filters.Regex('^🎥 YouTube to Reel$'), self.youtube_to_reel),
                    MessageHandler(filters.Regex('^⚙️ Settings$'), self.settings),
                    MessageHandler(filters.Regex('^📊 Analytics$'), self.analytics),
                    MessageHandler(filters.Regex('^🔍 AI Optimization$'), self.ai_optimization),
                    MessageHandler(filters.Regex('^◀️ Back$'), self.start),
                ],
                UPLOAD_CONTENT: [
                    MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, self.handle_upload),
                    MessageHandler(filters.Regex('^◀️ Back$'), self.main_menu),
                ],
                YOUTUBE_PROCESSING: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_youtube_link),
                    MessageHandler(filters.Regex('^◀️ Back$'), self.main_menu),
                ]
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )
        
        self.application.add_handler(conv_handler)
        self.application.add_handler(CommandHandler("help", self.help_command))
        
    def load_user_data(self):
        """Load user data from file"""
        try:
            if os.path.exists('user_data.json'):
                with open('user_data.json', 'r') as f:
                    self.user_data = json.load(f)
        except Exception as e:
            logger.error(f"Error loading user data: {e}")
    
    def save_user_data(self):
        """Save user data to file"""
        try:
            with open('user_data.json', 'w') as f:
                json.dump(self.user_data, f)
        except Exception as e:
            logger.error(f"Error saving user data: {e}")
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start command - niche selection"""
        user_id = str(update.effective_user.id)
        
        # Check if user already selected a niche
        if user_id in self.user_data and 'niche' in self.user_data[user_id]:
            return await self.main_menu(update, context)
        
        # Create keyboard with niche options
        keyboard = []
        row = []
        for i, (key, value) in enumerate(NICHES.items()):
            row.append(value)
            if (i + 1) % 2 == 0:  # 2 buttons per row
                keyboard.append(row)
                row = []
        if row:  # Add remaining buttons if any
            keyboard.append(row)
        
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "👋 Welcome to Social Media Automation Bot!\n\n"
            "To provide you with the best content strategy, please select your niche:",
            reply_markup=reply_markup
        )
        
        return NICHE_SELECTION
    
    async def niche_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle niche selection"""
        user_id = str(update.effective_user.id)
        niche_text = update.message.text
        
        # Find the niche key from the text
        niche = None
        for key, value in NICHES.items():
            if value == niche_text:
                niche = key
                break
        
        if not niche:
            await update.message.reply_text("Invalid niche selection. Please try again.")
            return NICHE_SELECTION
        
        # Save user niche
        if user_id not in self.user_data:
            self.user_data[user_id] = {}
        
        self.user_data[user_id]['niche'] = niche
        self.save_user_data()
        
        await update.message.reply_text(
            f"Great! You've selected the {niche_text} niche.\n\n"
            f"I'll now optimize content specifically for this niche to maximize your engagement and growth potential.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        return await self.main_menu(update, context)
    
    async def invalid_niche(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle invalid niche selection"""
        await update.message.reply_text(
            "Please select a valid niche from the options provided."
        )
        return NICHE_SELECTION
    
    async def main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Show main menu"""
        user_id = str(update.effective_user.id)
        niche = self.user_data[user_id].get('niche', 'general')
        niche_name = NICHES.get(niche, 'General')
        
        keyboard = [
            ['📤 Upload Content', '🎥 YouTube to Reel'],
            ['⚙️ Settings', '📊 Analytics'],
            ['🔍 AI Optimization']
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"🏠 Main Menu - {niche_name}\n\n"
            "What would you like to do today?",
            reply_markup=reply_markup
        )
        
        return MAIN_MENU
    
    async def upload_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle upload content option"""
        keyboard = [['◀️ Back']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "📤 Upload Content\n\n"
            "Please send me a photo or video to post on Instagram. "
            "I'll automatically optimize it for your niche and schedule it for the best time.",
            reply_markup=reply_markup
        )
        
        return UPLOAD_CONTENT
    
    async def youtube_to_reel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle YouTube to Reel option"""
        keyboard = [['◀️ Back']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "🎥 YouTube to Reel\n\n"
            "Send me a YouTube link and I'll:\n"
            "1. Download the video\n"
            "2. Find the most engaging clip (15-45 seconds)\n"
            "3. Convert to vertical format\n"
            "4. Add subtitles and optimize for Instagram\n"
            "5. Schedule for posting at the optimal time\n\n"
            "Please paste a YouTube URL:",
            reply_markup=reply_markup
        )
        
        return YOUTUBE_PROCESSING
    
    async def handle_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle file uploads"""
        user_id = str(update.effective_user.id)
        
        # Get the file
        if update.message.photo:
            file = await update.message.photo[-1].get_file()
            file_type = "photo"
        elif update.message.video:
            file = await update.message.video.get_file()
            file_type = "video"
        elif update.message.document:
            file = await update.message.document.get_file()
            file_type = "document"
        else:
            await update.message.reply_text("Unsupported file type. Please send a photo or video.")
            return UPLOAD_CONTENT
        
        # Download the file
        file_name = f"downloads/{user_id}_{int(time.time())}.{file_type}"
        os.makedirs('downloads', exist_ok=True)
        await file.download_to_drive(file_name)
        
        # Get user niche for optimization
        niche = self.user_data[user_id].get('niche', 'general')
        
        # Generate AI-optimized caption and hashtags
        caption, hashtags = self.ai_optimize_content(file_name, niche, file_type)
        
        # Add to upload queue (in a real implementation, this would connect to the Instagram bot)
        await update.message.reply_text(
            f"✅ Content received and optimized!\n\n"
            f"📝 Caption: {caption}\n\n"
            f"🏷️ Hashtags: {hashtags}\n\n"
            f"I've added this to the upload queue and will post it at the optimal time for maximum engagement."
        )
        
        return await self.main_menu(update, context)
    
    async def handle_youtube_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle YouTube link processing"""
        user_id = str(update.effective_user.id)
        youtube_url = update.message.text
        
        # Validate YouTube URL
        if not self.is_valid_youtube_url(youtube_url):
            await update.message.reply_text(
                "That doesn't look like a valid YouTube URL. Please try again."
            )
            return YOUTUBE_PROCESSING
        
        # Get user niche for optimization
        niche = self.user_data[user_id].get('niche', 'general')
        
        # Process the YouTube video (in a real implementation)
        await update.message.reply_text(
            "🔍 Analyzing YouTube video...\n\n"
            "I'm finding the most engaging segment and optimizing it for Instagram Reels."
        )
        
        # Simulate processing time
        time.sleep(2)
        
        # Generate AI-optimized content
        caption, hashtags = self.ai_generate_youtube_content(youtube_url, niche)
        
        await update.message.reply_text(
            f"✅ YouTube video processed!\n\n"
            f"📝 Caption: {caption}\n\n"
            f"🏷️ Hashtags: {hashtags}\n\n"
            f"I've added this to the upload queue and will post it at the optimal time for maximum engagement."
        )
        
        return await self.main_menu(update, context)
    
    async def settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Show settings menu"""
        user_id = str(update.effective_user.id)
        niche = self.user_data[user_id].get('niche', 'general')
        niche_name = NICHES.get(niche, 'General')
        
        keyboard = [
            ['Change Niche', 'Posting Schedule'],
            ['Content Preferences', 'AI Settings'],
            ['◀️ Back']
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"⚙️ Settings - Current Niche: {niche_name}\n\n"
            "Configure your automation preferences:",
            reply_markup=reply_markup
        )
        
        return MAIN_MENU
    
    async def analytics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Show analytics"""
        # In a real implementation, this would show actual analytics data
        keyboard = [['◀️ Back']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "📊 Account Analytics\n\n"
            "📈 Posts today: 3/10\n"
            "👀 Average views: 12,457\n"
            "👍 Average engagement: 8.7%\n"
            "🕒 Best posting time: 7:00 PM\n"
            "🔥 Top performing niche: " + NICHES.get(self.user_data.get(str(update.effective_user.id), {}).get('niche', 'general'), 'General') + "\n\n"
            "💡 Recommendation: Post more motivational content in the evening for higher engagement.",
            reply_markup=reply_markup
        )
        
        return MAIN_MENU
    
    async def ai_optimization(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """AI optimization menu"""
        keyboard = [
            ['Analyze Performance', 'Content Strategy'],
            ['Hashtag Analysis', 'Audience Insights'],
            ['◀️ Back']
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "🔍 AI Optimization Tools\n\n"
            "Leverage AI to improve your content strategy and growth:",
            reply_markup=reply_markup
        )
        
        return MAIN_MENU
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a help message"""
        await update.message.reply_text(
            "🤖 Social Media Automation Bot Help\n\n"
            "I can help you automate your Instagram content strategy:\n\n"
            "/start - Begin setup and niche selection\n"
            "/help - Show this help message\n\n"
            "Features:\n"
            "• 📤 Upload content directly\n"
            "• 🎥 Convert YouTube videos to Reels\n"
            "• 🔍 AI-powered optimization\n"
            "• 📊 Performance analytics\n"
            "• ⚙️ Customizable settings\n\n"
            "Select a niche to get content tailored to your audience!"
        )
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the conversation"""
        await update.message.reply_text(
            "Operation cancelled.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    def is_valid_youtube_url(self, url):
        """Check if the URL is a valid YouTube URL"""
        youtube_regex = (
            r'(https?://)?(www\.)?'
            r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
        
        return re.match(youtube_regex, url) is not None
    
    def ai_optimize_content(self, file_path, niche, content_type):
        """AI optimization for content (simulated)"""
        # In a real implementation, this would use ML models or API calls
        
        # Niche-specific content strategies
        niche_strategies = {
            'fitness': {
                'captions': [
                    "Transform your body in 30 days! 💪 #FitnessJourney\n\nWho's joining me? 👇",
                    "Form is everything! Proper technique prevents injury and maximizes results. 🏋️‍♂️\n\nSave this for your next workout!",
                    "The only bad workout is the one that didn't happen. Get after it! 🔥"
                ],
                'hashtags': '#fitness #workout #gym #health #fit #motivation #training #lifestyle #fitfam #gymlife'
            },
            'tech': {
                'captions': [
                    "This new tech is going to change everything! 🤯\n\nWhat do you think? 👇",
                    "Tech tip of the day: Always keep your software updated for security and performance! 🔒\n\nSave this tip!",
                    "The future is here, and it's amazing! This technology will revolutionize how we live. 🚀"
                ],
                'hashtags': '#technology #tech #gadgets #innovation #ai #future #digital #device #techie #techtips'
            },
            'business': {
                'captions': [
                    "This business strategy doubled my revenue in 30 days! 📈\n\nWant me to explain how? 👇",
                    "Entrepreneur tip: Focus on providing value, not just making sales. The money will follow. 💼\n\nAgree?",
                    "The most successful people invest in themselves first. Never stop learning! 📚"
                ],
                'hashtags': '#business #entrepreneur #success #motivation #marketing #startup #leadership #money #growth #hustle'
            }
        }
        
        # Default strategy if niche not found
        strategy = niche_strategies.get(niche, {
            'captions': [
                "Check out this amazing content! 🌟\n\nWhat do you think? 👇",
                "This is going to change your perspective! 💡\n\nSave for later! 📌",
                "You need to see this! 🔥\n\nShare with someone who needs to see this too!"
            ],
            'hashtags': '#viral #trending #explorepage #fyp #foryou #instagram #content #follow #like #share'
        })
        
        caption = random.choice(strategy['captions'])
        hashtags = strategy['hashtags']
        
        return caption, hashtags
    
    def ai_generate_youtube_content(self, youtube_url, niche):
        """AI content generation for YouTube videos (simulated)"""
        # In a real implementation, this would analyze the YouTube video content
        
        # Simulate different responses based on niche
        niche_responses = {
            'fitness': {
                'captions': [
                    "This workout technique from YouTube completely transformed my routine! 💪\n\nWatch and learn! 👇",
                    "I found this amazing fitness tutorial on YouTube that I had to share! 🏋️‍♂️\n\nSave this for your next workout!",
                    "Game-changing fitness advice from experts on YouTube! 🔥\n\nWho's trying this with me?"
                ]
            },
            'tech': {
                'captions': [
                    "This YouTube tech review saved me from buying the wrong product! 📱\n\nVery insightful! 👇",
                    "Amazing tech tutorial I found on YouTube that everyone should see! 🤯\n\nSave this for later!",
                    "This YouTube channel has the best tech tips I've ever seen! 🚀\n\nCheck it out!"
                ]
            },
            'business': {
                'captions': [
                    "This YouTube business strategy completely changed how I approach marketing! 📈\n\nMust watch! 👇",
                    "I found this incredible business advice on YouTube that doubled my revenue! 💼\n\nSave this!",
                    "Game-changing entrepreneurial advice from YouTube experts! 🔥\n\nWatch and implement!"
                ]
            }
        }
        
        # Default if niche not found
        strategy = niche_responses.get(niche, {
            'captions': [
                "Amazing content I found on YouTube that you need to see! 🌟\n\nCheck it out! 👇",
                "This YouTube video completely changed my perspective! 💡\n\nVery insightful!",
                "You need to watch this YouTube video! 🔥\n\nShare with others who need to see this too!"
            ]
        })
        
        caption = random.choice(strategy['captions'])
        hashtags = self.ai_optimize_content(None, niche, None)[1]  # Get hashtags from the other method
        
        return caption, hashtags

    def run(self):
        """Run the bot"""
        self.application.run_polling()

# Main execution
if __name__ == "__main__":
    # Get Telegram bot token from environment variable or config
    BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN_HERE')
    
    if BOT_TOKEN == 'YOUR_TELEGRAM_BOT_TOKEN_HERE':
        print("Please set the TELEGRAM_BOT_TOKEN environment variable")
        exit(1)
    
    bot = TelegramSocialBot(BOT_TOKEN)
    bot.run()