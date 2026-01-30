import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import yt_dlp
import re
import traceback

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ ERROR: BOT_TOKEN not found in environment!")
    logger.error("Set it in Railway: Settings → Variables")
    exit(1)

# Create downloads folder
os.makedirs("downloads", exist_ok=True)

class SimpleVideoBot:
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'outtmpl': 'downloads/%(title)s.%(ext)s',
        }
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Simple start command"""
        user = update.effective_user
        welcome_text = f"""
🤖 *Simple Video Downloader Bot*

👋 Hello {user.first_name}!

📥 *Send me any video URL from:*
• YouTube
• TikTok  
• Instagram
• Facebook
• Twitter/X
• Reddit
• 1000+ other sites

⚡ *How to use:*
1. Send video URL
2. Select quality
3. Download!

❓ *Commands:*
/start - Show this message
/help - Show help
/about - About this bot

🔥 *Note:* Bot runs on Railway cloud
"""
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command"""
        help_text = """
📚 *Help Guide*

🔗 *Supported Sites:*
- YouTube (youtube.com, youtu.be)
- TikTok (tiktok.com)
- Instagram (instagram.com)
- Twitter/X (twitter.com, x.com)
- Facebook (facebook.com)
- Reddit (reddit.com)
- Vimeo, Dailymotion, etc.

🎬 *How to Download:*
1. Copy video URL
2. Send to this bot
3. Select quality
4. Wait for download

⚡ *Tips:*
- Use direct video links
- Some sites may need login
- Max file size: 2GB

❓ *Problems?*
- Try different quality
- Check if video is available
- Contact if persistent issues
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def about(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """About command"""
        about_text = """
ℹ️ *About This Bot*

🤖 *Simple Video Downloader*
Version: 1.0
Platform: Railway Cloud

⚡ *Features:*
- Download from 1000+ sites
- Multiple quality options
- Audio extraction
- Fast & reliable

🔧 *Technology:*
- Python 3.11
- python-telegram-bot
- yt-dlp
- Railway hosting

📝 *Note:* This bot is for educational purposes only.
"""
        await update.message.reply_text(about_text, parse_mode='Markdown')
    
    def get_video_info(self, url: str):
        """Get video information"""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                formats = []
                for fmt in info.get('formats', []):
                    if fmt.get('vcodec') != 'none':  # Only video formats
                        format_data = {
                            'format_id': fmt['format_id'],
                            'ext': fmt.get('ext', 'mp4'),
                            'height': fmt.get('height', 0),
                            'width': fmt.get('width', 0),
                            'filesize': fmt.get('filesize', 0),
                            'quality': f"{fmt.get('height', 0)}p" if fmt.get('height') else 'N/A'
                        }
                        formats.append(format_data)
                
                # Sort by quality
                formats.sort(key=lambda x: x.get('height', 0), reverse=True)
                
                return {
                    'success': True,
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', 'Unknown'),
                    'formats': formats[:6],  # Max 6 formats
                    'webpage_url': url,
                }
        except Exception as e:
            logger.error(f"Video info error: {e}")
            return {'success': False, 'error': str(e)}
    
    def format_duration(self, seconds: int) -> str:
        """Format duration nicely"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds//60}:{seconds%60:02d}"
        else:
            return f"{seconds//3600}:{(seconds%3600)//60:02d}:{seconds%60:02d}"
    
    def format_size(self, bytes_size: int) -> str:
        """Format file size"""
        if bytes_size == 0:
            return "Unknown"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"
    
    async def handle_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle video URL"""
        url = update.message.text.strip()
        
        # Basic URL validation
        if not re.match(r'^https?://', url):
            await update.message.reply_text("❌ Please send a valid URL starting with http:// or https://")
            return
        
        # Show processing message
        msg = await update.message.reply_text("🔍 *Checking video...*", parse_mode='Markdown')
        
        # Get video info
        video_info = self.get_video_info(url)
        
        if not video_info.get('success'):
            await msg.edit_text(f"❌ Error: {video_info.get('error', 'Failed to get video info')}")
            return
        
        # Create keyboard with formats
        keyboard = []
        
        # Best quality option
        keyboard.append([InlineKeyboardButton("⚡ Best Quality", callback_data=f"dl:{url}:best")])
        
        # Audio only option
        keyboard.append([InlineKeyboardButton("🎵 Audio Only (MP3)", callback_data=f"audio:{url}")])
        
        # Video quality options
        for fmt in video_info['formats']:
            quality = fmt.get('quality', 'N/A')
            size = self.format_size(fmt.get('filesize', 0))
            if quality != 'N/A':
                text = f"📹 {quality} ({size})"
                keyboard.append([InlineKeyboardButton(text, callback_data=f"dl:{url}:{fmt['format_id']}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Prepare info text
        info_text = f"""
📹 *Video Found!*

📌 *Title:* {video_info['title']}
👤 *Uploader:* {video_info['uploader']}
⏱️ *Duration:* {self.format_duration(video_info['duration'])}

👇 *Select download option:*
"""
        
        # Send with thumbnail if available
        if video_info.get('thumbnail'):
            try:
                await update.message.reply_photo(
                    photo=video_info['thumbnail'],
                    caption=info_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                await msg.delete()
            except:
                await msg.edit_text(info_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await msg.edit_text(info_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button clicks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("dl:"):
            _, url, format_id = data.split(":", 2)
            await self.download_video(query, url, format_id)
        
        elif data.startswith("audio:"):
            url = data.split(":", 1)[1]
            await self.download_audio(query, url)
    
    async def download_video(self, query, url: str, format_id: str):
        """Download video"""
        msg = await query.message.reply_text("⏬ *Downloading video...*", parse_mode='Markdown')
        
        try:
            # Download options
            ydl_opts = {
                'format': format_id,
                'outtmpl': 'downloads/%(title)s.%(ext)s',
                'quiet': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                # Check if file exists (yt-dlp might change extension)
                if not os.path.exists(filename):
                    # Try common extensions
                    for ext in ['.webm', '.mkv', '.mp4', '.m4a']:
                        alt_file = filename.rsplit('.', 1)[0] + ext
                        if os.path.exists(alt_file):
                            filename = alt_file
                            break
            
            # Get file size
            file_size = os.path.getsize(filename)
            
            await msg.edit_text("📤 *Uploading to Telegram...*")
            
            # Send video (Telegram limit: 50MB for bots, 2GB for premium)
            try:
                with open(filename, 'rb') as f:
                    await query.message.reply_video(
                        video=f,
                        caption=f"✅ *Download Complete!*\n📹 {info.get('title', 'Video')}\n📦 Size: {self.format_size(file_size)}",
                        parse_mode='Markdown',
                        supports_streaming=True,
                        read_timeout=300,
                        write_timeout=300,
                        connect_timeout=300
                    )
                
                await msg.delete()
                
            except Exception as e:
                if "File too large" in str(e):
                    await msg.edit_text(f"❌ File too large ({self.format_size(file_size)}). Telegram bot limit is 50MB.")
                else:
                    await msg.edit_text(f"❌ Upload error: {str(e)}")
            
            # Cleanup
            try:
                os.remove(filename)
            except:
                pass
            
        except Exception as e:
            logger.error(f"Download error: {traceback.format_exc()}")
            await msg.edit_text(f"❌ Download failed: {str(e)}")
    
    async def download_audio(self, query, url: str):
        """Download audio only"""
        msg = await query.message.reply_text("🎵 *Extracting audio...*", parse_mode='Markdown')
        
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': 'downloads/%(title)s.%(ext)s',
                'quiet': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                filename = filename.rsplit('.', 1)[0] + '.mp3'
            
            file_size = os.path.getsize(filename)
            
            await msg.edit_text("📤 *Uploading audio...*")
            
            with open(filename, 'rb') as f:
                await query.message.reply_audio(
                    audio=f,
                    caption=f"✅ *Audio Extracted!*\n🎵 {info.get('title', 'Audio')}\n📦 Size: {self.format_size(file_size)}",
                    parse_mode='Markdown'
                )
            
            await msg.delete()
            
            # Cleanup
            try:
                os.remove(filename)
            except:
                pass
            
        except Exception as e:
            logger.error(f"Audio error: {traceback.format_exc()}")
            await msg.edit_text(f"❌ Audio extraction failed: {str(e)}")

def main():
    """Start the bot"""
    print(f"""
╔══════════════════════════════════╗
║     SIMPLE VIDEO DOWNLOADER      ║
║         🤖 BOT v1.0             ║
╚══════════════════════════════════╝
    
✅ Token loaded: {BOT_TOKEN[:15]}...
✅ Downloads folder ready
✅ Starting bot on Railway...
    """)
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Initialize bot
    bot = SimpleVideoBot()
    
    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help))
    application.add_handler(CommandHandler("about", bot.about))
    
    # Handle URLs
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        bot.handle_url
    ))
    
    # Handle button clicks
    application.add_handler(CallbackQueryHandler(bot.button_callback))
    
    # Start polling
    print("🤖 Bot is running...")
    print("📱 Send /start to your bot on Telegram")
    
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == '__main__':
    main()
