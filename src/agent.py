import asyncio
from asyncio.log import logger
from datetime import datetime
import json
import logging
import os
import sys
import yaml
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# AI Models
from models import GroqAI

# Blockchain
from blockchain.solana.wallet import SolanaWallet 
from blockchain.ethereum.wallet import EthereumWallet

# Cognition
from cognition.memory import MemoryManager
from cognition.reasoning import ReasoningEngine
from cognition.context import ContextManager
from cognition.goals import GoalManager
from cognition.learning import LearningManager

# Community
from community.content.generator import ContentGenerator

# Investment
from investment.analysis.market_analysis import MarketAnalyzer
from investment.analysis.sentiment_analysis import SentimentAnalyzer

# Utils
from utils.errors import SecurityError, AgentError
from utils.security import SecurityService
from utils.error_handler import ErrorHandler

class AgentConfig:
    """Agent configuration with proper validation"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self._config: Dict[str, Any] = {}
        
        # Default configuration
        self.defaults = {
            'twitter_username': None,
            'loop_interval': 5,
            'max_retries': 3,
            'log_level': 'INFO',
        }
        
        if config_path:
            self.load_config(config_path)
        else:
            self._config = self.defaults.copy()
    
    def load_config(self, config_path: str) -> None:
        """Load configuration from file with validation"""
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                
            # Merge with defaults
            self._config = {**self.defaults, **config_data}
            
            # Validate required fields
            self._validate_config()
            
        except Exception as e:
            self.logger.error(f"Error loading config: {str(e)}")
            self._config = self.defaults.copy()
    
    def _validate_config(self) -> None:
        """Validate configuration values"""
        if not self._config.get('twitter_username'):
            self.logger.warning("Twitter username not configured")
            
        if not isinstance(self._config.get('loop_interval'), (int, float)):
            self.logger.warning("Invalid loop_interval, using default")
            self._config['loop_interval'] = self.defaults['loop_interval']
            
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with default"""
        return self._config.get(key, default)
    
    @property
    def twitter_username(self) -> Optional[str]:
        """Get Twitter username with validation"""
        return self._config.get('twitter_username')
    
    @property
    def loop_interval(self) -> int:
        """Get loop interval with validation"""
        return int(self._config.get('loop_interval', self.defaults['loop_interval']))

class Agent:
    def __init__(self, config: AgentConfig, api_keys: Dict[str, str]):
        self.config = config
        self.api_keys = api_keys
        self.logger = logging.getLogger(self.config.name)
        
        # Load configurations first
        self.settings = self._load_settings()
        self.personality = self._load_personality()
        
        # Initialize security first
        self.security = SecurityService(
            config=self.settings.get('security', {
                'max_retries': 3,
                'error_cooldown': 5,
                'signing_key': self.settings.get('security', {}).get('signing_key', 'default_key')
            })
        )
        
        # Initialize error handler early
        self.error_handler = ErrorHandler(
            config=self.settings.get('error_handling', {
                'max_retries': 3,
                'error_cooldown': 5
            })
        )

        # Initialize AI models first
        self.groq = GroqAI(
            api_key=api_keys["groq"],
            model=self.settings.get("ai", {}).get("groq_model", "mixtral-8x7b-32768")
        )

        # Initialize content generator after AI model
        self.content_generator = ContentGenerator(
            config=self.settings.get('content', {
                'content_schedule': {
                    'market_update': [9, 13, 17],
                    'technical_analysis': [10, 14, 18],
                    'community_update': [11, 15, 19]
                },
                'content_templates': {
                    'market_update': "Generate a market update focused on...",
                    'technical_analysis': "Analyze the following technical indicators...",
                    'community_update': "Create a community update highlighting..."
                },
                'default_template': "Generate a general update about..."
            }),
            ai_service=self.groq
        )
        
        # Initialize core components
        self.memory = MemoryManager()
        self.reasoning = ReasoningEngine()
        self.context = ContextManager()
        self.goals = GoalManager()
        self.learning = LearningManager()
        
        # Market Analysis
        market_data_sources = self.settings.get("market_analysis", {}).get("data_sources", {})
        self.market_analyzer = MarketAnalyzer(data_sources=market_data_sources)
        self.sentiment_analyzer = SentimentAnalyzer(data_sources={"social": "twitter"})

        # Initialize wallets
        self.solana_wallet = SolanaWallet(api_keys["solana_rpc"])
        self.ethereum_wallet = EthereumWallet(
            rpc_url=api_keys.get("ethereum_rpc") or "https://eth-mainnet.g.alchemy.com/v2/demo",
            private_key=api_keys.get("eth_private_key"),
            zksync_url=api_keys.get("zksync_rpc")
        )

    def _load_settings(self) -> Dict:
        self.logger.debug(f"Loading settings from {self.config.settings_path}")
        with open(self.config.settings_path) as f:
            return yaml.safe_load(f)

    def _load_personality(self) -> Dict:
        self.logger.debug(f"Loading personality from {self.config.personality_path}")
        with open(self.config.personality_path) as f:
            return yaml.safe_load(f)

    async def _initialize_systems(self):
        """Initialize all system components"""
        try:
            # Initialize AI first
            logger.info("Initializing AI service...")
            await self.groq.initialize()
                
            # Initialize other systems
            logger.info("Initializing other systems...")
            systems = [
                self.memory,
                self.reasoning,
                self.context,
                self.goals,
                self.learning,
                self.market_analyzer,
                self.sentiment_analyzer,
                self.solana_wallet,
                self.ethereum_wallet
            ]
            
            results = await asyncio.gather(
                *(system.initialize() for system in systems),
                return_exceptions=True
            )
            
            # Check for initialization failures
            for system, result in zip(systems, results):
                if isinstance(result, Exception):
                    self.logger.error(f"Failed to initialize {system.__class__.__name__}: {result}")
                    raise result
            
            self.logger.info("All systems initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize systems: {e}")
            raise

    async def cleanup(self) -> None:
        """Cleanup agent resources"""
        try:
            cleanup_tasks = [
                self.groq.cleanup() if hasattr(self.groq, 'cleanup') else None,
                self.memory.cleanup() if hasattr(self.memory, 'cleanup') else None,
                self.security.cleanup() if hasattr(self.security, 'cleanup') else None,
                self.solana_wallet.cleanup() if hasattr(self.solana_wallet, 'cleanup') else None,
                self.ethereum_wallet.cleanup() if hasattr(self.ethereum_wallet, 'cleanup') else None
            ]
            
            # Filter out None tasks
            cleanup_tasks = [task for task in cleanup_tasks if task is not None]
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks)
                
            self.logger.info("Agent cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    async def start(self):
        """Start the agent and all its components"""
        try:
            self.logger.info("Starting agent...")
            await self._initialize_systems()

            await asyncio.gather(
                self._run_cognition_loop(),
                self._run_investment_loop(),
                self._run_community_loop(),
                self._run_research_loop(),
            )
        except Exception as e:
            self.logger.error(f"Error starting agent: {e}")
            await self.handle_error(e)
            raise

    async def _run_cognition_loop(self):
        """Run the main cognitive processing loop"""
        while True:
            try:
                # Update Context
                current_context = await self.context.get_current_context()
                
                # Process Active Goals
                active_goals = await self.goals.get_active_goals()
                for goal in active_goals:
                    # Get relevant memories
                    relevant_memories = await self.memory.get_relevant_memories(
                        goal, current_context
                    )
                    
                    # Analyze with reasoning engine
                    analysis = await self.reasoning.analyze_goal(
                        goal=goal,
                        context=current_context,
                        memories=relevant_memories
                    )
                    
                    # Execute actions
                    actions = await self.determine_actions(analysis)
                    for action in actions:
                        result = await self.execute_action(action)
                        await self.learning.learn_from_action(action, result)
                
                # Generate New Goals
                new_goals = await self._generate_new_goals(current_context)
                for goal in new_goals:
                    await self.goals.add_goal(**goal)
                
                await asyncio.sleep(self.settings.get("cognition", {}).get("cycle_interval", 10))
                
            except Exception as e:
                self.logger.error(f"Error in cognition loop: {e}")
                await self.handle_error(e)
                await asyncio.sleep(5)

    async def _run_investment_loop(self):
        """Run the investment management loop"""
        while True:
            try:
                # Analyze market with security verification
                if await self.security.verify_data_sources([
                    self.market_analyzer,
                    self.sentiment_analyzer
                ]):
                    market_data = await self.market_analyzer.get_market_overview()
                    sentiment_data = await self.sentiment_analyzer.analyze_social_sentiment()

                    # Get AI analysis
                    analysis = await self.groq.analyze_market({
                        "market_data": market_data,
                        "sentiment": sentiment_data,
                        "portfolio": await self.get_portfolio_status()
                    })

                    # Execute trades if needed
                    if analysis.get("recommended_actions"):
                        for action in analysis["recommended_actions"]:
                            await self.execute_trade(action)

                # Sleep between iterations
                await asyncio.sleep(self.settings.get("investment", {}).get("scan_interval", 60))

            except Exception as e:
                self.logger.error(f"Error in investment loop: {e}")
                await self.handle_error(e)
                await asyncio.sleep(5)

    async def _run_community_loop(self):
        """Manage community engagement and social presence"""
        while True:
            try:
                # Generate and post content
                content = await self.content_generator.generate_content()
                
                # Post to social channels
                await self.post_to_social_channels(content)

                # Engage with community
                await self.process_social_interactions()
                
                await asyncio.sleep(self.settings.get("community", {}).get("update_interval", 300))
            except Exception as e:
                self.logger.error(f"Error in community loop: {e}")
                await self.handle_error(e)
                await asyncio.sleep(5)

    async def _run_research_loop(self):
        """Run research and analysis tasks"""
        while True:
            try:
                # Market research
                market_trends = await self._analyze_market_trends()
                
                # Competition analysis
                competition = await self._analyze_competition()
                
                # Generate report
                await self._generate_research_report({
                    "trends": market_trends,
                    "competition": competition,
                    "portfolio": await self.get_portfolio_status()
                })
                
                await asyncio.sleep(self.settings.get("research", {}).get("interval", 3600))
            except Exception as e:
                self.logger.error(f"Error in research loop: {e}")
                await self.handle_error(e)
                await asyncio.sleep(5)

    async def handle_error(self, error: Exception, context: Optional[Dict] = None):
        """Handle agent errors with error handler"""
        await self.error_handler.handle_error(error, context)

    async def post_to_social_channels(self, content: Dict):
        """Post content to configured social channels"""
        try:
            tasks = []
            
            if self.settings.get("social", {}).get("twitter", {}).get("enabled"):
                tasks.append(self._post_to_twitter(content))
                
            if self.settings.get("social", {}).get("discord", {}).get("enabled"):
                tasks.append(self._post_to_discord(content))
                
            await asyncio.gather(*tasks)
            
        except Exception as e:
            self.logger.error(f"Error posting to social channels: {e}")
            await self.handle_error(e)

    async def process_social_interactions(self):
        """Process and respond to social interactions"""
        try:
            # Process mentions and messages
            await self._process_twitter_mentions()
            await self._process_discord_messages()
            
            # Track engagement metrics
            await self._update_engagement_metrics()
            
        except Exception as e:
            self.logger.error(f"Error processing social interactions: {e}")
            await self.handle_error(e)

    async def execute_trade(self, trade_params: Dict) -> Dict:
        """Execute a trade with security checks"""
        try:
            # Validate trade parameters
            if not await self.security.verify_trade(trade_params):
                raise SecurityError("Trade verification failed")
                
            # Execute on appropriate chain
            if trade_params.get("chain") == "solana":
                result = await self.solana_wallet.execute_trade(trade_params)
            else:
                result = await self.ethereum_wallet.execute_trade(trade_params)
                
            # Update portfolio and notify
            await self._update_portfolio(result)
            await self._notify_trade(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing trade: {e}")
            await self.handle_error(e)
            return {"status": "failed", "error": str(e)}

    async def determine_actions(self, analysis: Dict) -> List[Dict]:
        """Determine actions based on analysis"""
        try:
            prompt = (
                f"Based on this analysis:\n{analysis}\n\n"
                "Determine the specific actions to take. Consider:\n"
                "1. Market conditions\n"
                "2. Risk levels\n"
                "3. Portfolio status\n"
                "4. Available resources\n\n"
                "Return a list of actionable steps."
            )
            
            response = await self.groq.generate_response(prompt)
            return self._parse_actions(response)
            
        except Exception as e:
            self.logger.error(f"Error determining actions: {e}")
            await self.handle_error(e)
            return []

    async def get_portfolio_status(self) -> Dict:
        """Get current portfolio status"""
        try:
            sol_balance = await self.solana_wallet.get_balance()
            eth_balance = await self.ethereum_wallet.get_balance()
            
            return {
                "solana": sol_balance,
                "ethereum": eth_balance,
                "total_value_usd": await self._calculate_total_value()
            }
        except Exception as e:
            self.logger.error(f"Error getting portfolio status: {e}")
            await self.handle_error(e)
            return {}
# Continue Agent class implementation

    async def _analyze_market_trends(self) -> Dict:
        """Analyze current market trends"""
        try:
            # Gather market data
            market_data = await self.market_analyzer.get_market_data()
            
            # Get AI analysis of trends
            analysis = await self.groq.analyze_market({
                "market_data": market_data,
                "timeframe": "7d",
                "metrics": [
                    "volume",
                    "price_action",
                    "social_sentiment",
                    "on_chain_activity"
                ]
            })
            
            return analysis
        except Exception as e:
            self.logger.error(f"Error analyzing market trends: {e}")
            await self.handle_error(e)
            return {}

    async def _analyze_competition(self) -> Dict:
        """Analyze competitive landscape"""
        try:
            competitors = self.settings.get("research", {}).get("competitors", [])
            
            competitor_data = {}
            for competitor in competitors:
                data = await self._gather_competitor_data(competitor)
                competitor_data[competitor] = data
            
            analysis = await self.groq.generate_response(
                prompt=f"Analyze these competitors: {competitor_data}",
                temperature=0.3
            )
            
            return {
                "raw_data": competitor_data,
                "analysis": analysis
            }
        except Exception as e:
            self.logger.error(f"Error analyzing competition: {e}")
            await self.handle_error(e)
            return {}

    async def _gather_competitor_data(self, competitor: str) -> Dict:
        """Gather data about a specific competitor"""
        try:
            return {
                "social_metrics": await self._get_social_metrics(competitor),
                "market_metrics": await self._get_market_metrics(competitor),
                "tech_analysis": await self._analyze_tech_stack(competitor)
            }
        except Exception as e:
            self.logger.error(f"Error gathering competitor data: {e}")
            await self.handle_error(e)
            return {}

    async def _generate_research_report(self, data: Dict) -> None:
        """Generate and store research report"""
        try:
            # Generate report using AI
            report_content = await self.groq.generate_response(
                prompt=f"Generate detailed research report from: {data}",
                system_prompt="You are a crypto market research analyst. Generate a comprehensive report.",
                max_tokens=2000
            )
            
            # Format report
            report = {
                "timestamp": datetime.now().isoformat(),
                "content": report_content,
                "data": data,
                "summary": await self._generate_report_summary(report_content)
            }
            
            # Store report
            await self.memory.store_research(report)
            
            # Notify relevant parties
            await self._distribute_report(report)
            
        except Exception as e:
            self.logger.error(f"Error generating research report: {e}")
            await self.handle_error(e)

    async def _post_to_twitter(self, content: Dict) -> None:
        """Post content to Twitter"""
        try:
            if not content.get("content"):
                raise ValueError("No content provided for Twitter post")
                
            # Format content for Twitter
            tweet = await self._format_for_twitter(content["content"])
            
            # Post using Twitter API client
            # Add actual Twitter posting logic here
            self.logger.info(f"Would post to Twitter: {tweet}")
            
        except Exception as e:
            self.logger.error(f"Error posting to Twitter: {e}")
            await self.handle_error(e)

    async def _post_to_discord(self, content: Dict) -> None:
        """Post content to Discord"""
        try:
            if not content.get("content"):
                raise ValueError("No content provided for Discord post")
                
            # Format content for Discord
            message = await self._format_for_discord(content["content"])
            
            # Post to appropriate Discord channels
            channels = self.settings.get("social", {}).get("discord", {}).get("channels", [])
            for channel in channels:
                # Add actual Discord posting logic here
                self.logger.info(f"Would post to Discord channel {channel}: {message}")
                
        except Exception as e:
            self.logger.error(f"Error posting to Discord: {e}")
            await self.handle_error(e)

    async def _process_twitter_mentions(self) -> None:
        """Process and respond to Twitter mentions"""
        try:
            # Get recent mentions
            # Add Twitter API integration here
            mentions = []  # Placeholder for actual Twitter mentions
            
            for mention in mentions:
                response = await self._generate_social_response(mention)
                # Add actual Twitter reply logic here
                self.logger.info(f"Would reply to Twitter mention: {response}")
                
        except Exception as e:
            self.logger.error(f"Error processing Twitter mentions: {e}")
            await self.handle_error(e)

    async def _process_discord_messages(self) -> None:
        """Process and respond to Discord messages"""
        try:
            # Get recent messages
            # Add Discord API integration here
            messages = []  # Placeholder for actual Discord messages
            
            for message in messages:
                response = await self._generate_social_response(message)
                # Add actual Discord reply logic here
                self.logger.info(f"Would reply to Discord message: {response}")
                
        except Exception as e:
            self.logger.error(f"Error processing Discord messages: {e}")
            await self.handle_error(e)

    async def _update_engagement_metrics(self) -> None:
        """Update social engagement metrics"""
        try:
            metrics = {
                "twitter": await self._get_twitter_metrics(),
                "discord": await self._get_discord_metrics()
            }
            
            # Store metrics
            await self.memory.store_metrics(metrics)
            
            # Analyze engagement trends
            await self._analyze_engagement_trends(metrics)
            
        except Exception as e:
            self.logger.error(f"Error updating engagement metrics: {e}")
            await self.handle_error(e)

    async def _generate_social_response(self, message: Dict) -> str:
        """Generate appropriate response to social interaction"""
        try:
            context = {
                "platform": message.get("platform"),
                "user": message.get("user"),
                "content": message.get("content"),
                "sentiment": await self._analyze_message_sentiment(message)
            }
            
            response = await self.groq.generate_response(
                prompt=f"Generate response to: {message}",
                context=context,
                temperature=0.7
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error generating social response: {e}")
            await self.handle_error(e)
            return ""

    async def _analyze_message_sentiment(self, message: Dict) -> Dict:
        """Analyze sentiment of social message"""
        try:
            return await self.groq.analyze_sentiment(message.get("content", ""))
        except Exception as e:
            self.logger.error(f"Error analyzing message sentiment: {e}")
            await self.handle_error(e)
            return {"score": 0, "label": "neutral"}

    def _parse_actions(self, response: str) -> List[Dict]:
        """Parse AI response into actionable items"""
        try:
            # Attempt to parse as JSON first
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # Fall back to text parsing if not JSON
                actions = []
                for line in response.split('\n'):
                    if line.strip() and not line.startswith('#'):
                        actions.append({"action": line.strip()})
                return actions
                
        except Exception as e:
            self.logger.error(f"Error parsing actions: {e}")
            return []

    async def _calculate_total_value(self) -> float:
        """Calculate total portfolio value in USD"""
        try:
            # Get token prices
            prices = await self._get_token_prices()
            
            # Calculate total value
            sol_value = float(await self.solana_wallet.get_balance()) * prices.get("SOL", 0)
            eth_value = float(await self.ethereum_wallet.get_balance()) * prices.get("ETH", 0)
            
            return sol_value + eth_value
            
        except Exception as e:
            self.logger.error(f"Error calculating total value: {e}")
            await self.handle_error(e)
            return 0.0
# Final methods for Agent class

    async def _update_portfolio(self, trade_result: Dict) -> None:
        """Update portfolio after trade execution"""
        try:
            # Verify trade result
            if not await self.security.verify_trade_result(trade_result):
                raise SecurityError("Invalid trade result")
            
            # Update portfolio metrics
            portfolio_update = {
                "timestamp": datetime.now().isoformat(),
                "trade": trade_result,
                "balances": await self.get_portfolio_status()
            }
            
            # Store update
            await self.memory.store_portfolio_update(portfolio_update)
            
            # Update performance metrics
            await self._update_performance_metrics(portfolio_update)
            
        except Exception as e:
            self.logger.error(f"Error updating portfolio: {e}")
            await self.handle_error(e)

    async def _notify_trade(self, trade_result: Dict) -> None:
        """Send trade notifications"""
        try:
            # Prepare notification
            notification = await self._prepare_trade_notification(trade_result)
            
            # Send notifications through configured channels
            notification_tasks = []
            
            if self.settings.get("notifications", {}).get("discord", {}).get("enabled"):
                notification_tasks.append(self._post_to_discord(notification))
                
            if self.settings.get("notifications", {}).get("twitter", {}).get("enabled"):
                notification_tasks.append(self._post_to_twitter(notification))
            
            await asyncio.gather(*notification_tasks)
            
        except Exception as e:
            self.logger.error(f"Error notifying trade: {e}")
            await self.handle_error(e)

    async def _prepare_trade_notification(self, trade_result: Dict) -> Dict:
        """Prepare trade notification content"""
        try:
            # Generate notification text using AI
            context = {
                "trade": trade_result,
                "portfolio": await self.get_portfolio_status(),
                "market_conditions": await self._analyze_market_trends()
            }
            
            content = await self.groq.generate_response(
                prompt="Generate trade notification",
                context=context,
                temperature=0.7
            )
            
            return {
                "content": content,
                "type": "trade_notification",
                "data": trade_result
            }
            
        except Exception as e:
            self.logger.error(f"Error preparing trade notification: {e}")
            await self.handle_error(e)
            return {}

    async def _update_performance_metrics(self, portfolio_update: Dict) -> None:
        """Update agent performance metrics"""
        try:
            metrics = {
                "portfolio_value": await self._calculate_total_value(),
                "trade_count": await self._get_trade_count(),
                "win_rate": await self._calculate_win_rate(),
                "profit_loss": await self._calculate_profit_loss(),
                "timestamp": datetime.now().isoformat()
            }
            
            await self.memory.store_metrics(metrics)
            
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {e}")
            await self.handle_error(e)

    async def _get_trade_count(self) -> Dict:
        """Get trading statistics"""
        try:
            trades = await self.memory.get_trades(
                timeframe=self.settings.get("metrics", {}).get("timeframe", "24h")
            )
            
            return {
                "total": len(trades),
                "successful": len([t for t in trades if t.get("status") == "success"]),
                "failed": len([t for t in trades if t.get("status") == "failed"])
            }
            
        except Exception as e:
            self.logger.error(f"Error getting trade count: {e}")
            await self.handle_error(e)
            return {"total": 0, "successful": 0, "failed": 0}

    async def _calculate_win_rate(self) -> float:
        """Calculate trading win rate"""
        try:
            trade_counts = await self._get_trade_count()
            if trade_counts["total"] == 0:
                return 0.0
                
            return trade_counts["successful"] / trade_counts["total"]
            
        except Exception as e:
            self.logger.error(f"Error calculating win rate: {e}")
            await self.handle_error(e)
            return 0.0

    async def _calculate_profit_loss(self) -> Dict:
        """Calculate profit/loss metrics"""
        try:
            trades = await self.memory.get_trades(
                timeframe=self.settings.get("metrics", {}).get("timeframe", "24h")
            )
            
            total_profit = sum(t.get("profit", 0) for t in trades)
            total_loss = sum(t.get("loss", 0) for t in trades)
            
            return {
                "total_profit": total_profit,
                "total_loss": total_loss,
                "net_pnl": total_profit - total_loss
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating profit/loss: {e}")
            await self.handle_error(e)
            return {"total_profit": 0, "total_loss": 0, "net_pnl": 0}

    async def _get_token_prices(self) -> Dict[str, float]:
        """Get current token prices"""
        try:
            # Use configured price sources
            price_source = self.settings.get("price_source", "jupiter")
            
            if price_source == "jupiter":
                return await self._get_jupiter_prices()
            else:
                return await self._get_backup_prices()
                
        except Exception as e:
            self.logger.error(f"Error getting token prices: {e}")
            await self.handle_error(e)
            return {}

    async def _get_jupiter_prices(self) -> Dict[str, float]:
        """Get prices from Jupiter"""
        try:
            tokens = self.settings.get("tokens", ["SOL", "ETH"])
            prices = {}
            
            for token in tokens:
                try:
                    price = await self._fetch_jupiter_price(token)
                    prices[token] = price
                except Exception as e:
                    self.logger.error(f"Error getting {token} price: {e}")
                    continue
                    
            return prices
            
        except Exception as e:
            self.logger.error(f"Error getting Jupiter prices: {e}")
            await self.handle_error(e)
            return {}
    async def _generate_new_goals(self, current_context: Dict) -> List[Dict]:
        """Generate new goals based on current context"""
        try:
            # Generate goals using AI model
            response = await self.groq.generate_response(
                prompt=f"Based on current context, generate new goals:\n{json.dumps(current_context, indent=2)}",
                system_prompt=self.personality.get('goal_generation_prompt', 
                    "You are an AI agent managing crypto assets and community. Generate strategic goals.")
            )
            
            # Parse goals from response
            try:
                goals = json.loads(response)
                if isinstance(goals, dict) and 'goals' in goals:
                    return goals['goals']
                return []
            except json.JSONDecodeError:
                self.logger.error("Failed to parse goals from AI response")
                return []
                
        except Exception as e:
            self.logger.error(f"Error generating goals: {e}")
            await self.handle_error(e)
            return []

    async def _fetch_jupiter_price(self, token: str) -> float:
        """Fetch token price from Jupiter API"""
        try:
            from blockchain.solana.trades import JupiterTrader
            
            # Initialize Jupiter trader if not exists
            if not hasattr(self, '_jupiter_trader'):
                self._jupiter_trader = JupiterTrader()
            
            # Get price
            price_data = await self._jupiter_trader.get_token_price(token)
            if price_data.get('success'):
                return price_data['price']
            
            self.logger.error(f"Failed to fetch price for {token}")
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Error fetching {token} price: {e}")
            return 0.0

    async def _get_twitter_metrics(self, username: Optional[str] = None) -> Dict:
        """Get Twitter metrics with proper error handling"""
        try:
            if username is None:
                username = self.settings.get('social', {}).get('twitter', {}).get('username')
                if not username:
                    raise ValueError("Twitter username not configured")

            # Placeholder for Twitter API integration
            # Replace with actual Twitter API calls
            metrics = {
                "followers": 0,
                "engagement_rate": 0.0,
                "tweet_count": 0,
                "timestamp": datetime.now().isoformat()
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting Twitter metrics: {e}")
            return {}

    async def _get_discord_metrics(self) -> Dict:
        """Get Discord metrics with proper error handling"""
        try:
            # Placeholder for Discord API integration
            # Replace with actual Discord API calls
            metrics = {
                "members": 0,
                "active_users": 0,
                "message_count": 0,
                "timestamp": datetime.now().isoformat()
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting Discord metrics: {e}")
            return {}

    async def _generate_report_summary(self, report_content: str) -> str:
        """Generate concise summary of report content"""
        try:
            # Use AI to generate summary
            summary = await self.groq.generate_response(
                prompt=f"Summarize this report in 2-3 sentences:\n{report_content}",
                system_prompt="You are a research analyst. Create a concise summary.",
                max_tokens=150
            )
            
            return summary.strip()
            
        except Exception as e:
            self.logger.error(f"Error generating report summary: {e}")
            return "Summary generation failed"

    async def _format_for_twitter(self, content: str) -> str:
        """Format content for Twitter with character limit"""
        try:
            if len(content) <= 280:
                return content
                
            # Use AI to shorten content
            shortened = await self.groq.generate_response(
                prompt=f"Shorten this to fit Twitter's 280 character limit while maintaining key information:\n{content}",
                system_prompt="You are a social media expert. Create concise tweets.",
                max_tokens=100
            )
            
            return shortened[:280]
            
        except Exception as e:
            self.logger.error(f"Error formatting for Twitter: {e}")
            return content[:280]

    async def _format_for_discord(self, content: str) -> str:
        """Format content for Discord with proper formatting"""
        try:
            # Add Discord markdown formatting
            formatted = f"```\nMarket Update\n\n{content}\n```"
            return formatted
            
        except Exception as e:
            self.logger.error(f"Error formatting for Discord: {e}")
            return content

    async def _get_social_metrics(self, target: str) -> Dict:
        """Get social metrics for target"""
        try:
            return {
                "twitter": await self._get_twitter_metrics(target),
                "discord": await self._get_discord_metrics()
            }
        except Exception as e:
            self.logger.error(f"Error getting social metrics: {e}")
            return {}

    async def _get_market_metrics(self, target: str) -> Dict:
        """Get market metrics for target"""
        try:
            # Implement market metrics collection
            return {}
        except Exception as e:
            self.logger.error(f"Error getting market metrics: {e}")
            return {}

    async def _analyze_tech_stack(self, target: str) -> Dict:
        """Analyze technical aspects of target"""
        try:
            # Implement tech analysis
            return {}
        except Exception as e:
            self.logger.error(f"Error analyzing tech stack: {e}")
            return {}

    async def _analyze_engagement_trends(self, metrics: Dict) -> None:
        """Analyze social engagement trends"""
        try:
            # Implement trend analysis
            pass
        except Exception as e:
            self.logger.error(f"Error analyzing engagement trends: {e}")
    async def cleanup(self) -> None:
        """Cleanup agent resources"""
        try:
            cleanup_tasks = [
                self.groq.cleanup(),
                self.memory.cleanup(),
                self.security.cleanup(),
                self.solana_wallet.cleanup(),
                self.ethereum_wallet.cleanup()
            ]
            
            await asyncio.gather(*cleanup_tasks)
            self.logger.info("Agent cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            # Don't raise here as we're already cleaning up
if __name__ == "__main__":
    async def main():
        agent = None
        try:
            load_dotenv()
            agent_config = AgentConfig(config_path="config/agent_config.yaml")
            agent = Agent(config=agent_config)
            
            await agent.start()
                
        except KeyboardInterrupt:
            if agent:
                await agent.cleanup()
            logging.info("Shutting down agent...")
                
        except Exception as e:
            logging.error(f"Critical error: {e}")
            if agent:
                await agent.cleanup()
            sys.exit(1)

    asyncio.run(main())