"""
Main application entry point for new tinyDisplay architecture.
"""

import time
import asyncio
from pathlib import Path

from data.data_manager import DataManager
from reactive.dynamic_values import DynamicValuesEngine
from widgets.manager import WidgetManager
from rendering.controller import RenderController
from rendering.speculative import SpeculativeRenderer
from dsl.application import load_application_config

class TinyDisplayApp:
    """Main tinyDisplay application"""
    
    def __init__(self, config_path: str = "dsl/application.yaml"):
        self.config_path = config_path
        
        # Initialize core components
        self.data_manager = DataManager()
        self.dynamic_values_engine = DynamicValuesEngine(self.data_manager)
        self.widget_manager = WidgetManager(self.dynamic_values_engine)
        self.render_controller = RenderController(target_fps=60)
        self.speculative_renderer = SpeculativeRenderer(num_workers=3)
        
        # Load application configuration
        self.config = load_application_config(config_path)
        
    async def initialize(self):
        """Initialize the application"""
        print("🚀 Initializing tinyDisplay...")
        
        # Set up data streams
        await self._setup_data_streams()
        
        # Create dynamic values
        await self._setup_dynamic_values()
        
        # Create widgets
        await self._setup_widgets()
        
        # Start background services
        self.speculative_renderer.start_background_rendering()
        
        print("✅ tinyDisplay initialized successfully")
    
    async def run(self):
        """Run the main application loop"""
        print("🎬 Starting tinyDisplay main loop...")
        
        try:
            while True:
                current_time = time.time()
                
                # Process frame
                if self.render_controller.should_render_frame(current_time):
                    render_results = self.render_controller.process_frame(current_time)
                    
                    # Send to display hardware
                    await self._update_display(render_results)
                
                # Small sleep to prevent CPU spinning
                await asyncio.sleep(0.001)  # 1ms
                
        except KeyboardInterrupt:
            print("\n🛑 Shutting down tinyDisplay...")
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the application"""
        self.speculative_renderer.stop()
        print("👋 tinyDisplay shutdown complete")
    
    async def _setup_data_streams(self):
        """Set up data streams from configuration"""
        for stream_config in self.config.get('data_streams', []):
            self.data_manager.register_data_stream(
                stream_config['key'],
                stream_config
            )
    
    async def _setup_dynamic_values(self):
        """Set up dynamic values from configuration"""
        for name, dv_config in self.config.get('dynamic_values', {}).items():
            self.dynamic_values_engine.create_dynamic_value(
                name,
                dv_config['expression']
            )
    
    async def _setup_widgets(self):
        """Set up widgets from configuration"""
        for name, widget_config in self.config.get('widgets', {}).items():
            self.widget_manager.create_widget(
                widget_id=name,
                widget_type=widget_config['type'],
                config=widget_config
            )
    
    async def _update_display(self, render_results):
        """Update physical display with render results"""
        # TODO: Integrate with luma.oled/luma.lcd
        # This is where you'd send the rendered content to the actual display
        pass

async def main():
    """Main entry point"""
    app = TinyDisplayApp()
    
    await app.initialize()
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())
