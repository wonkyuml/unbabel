import os
import asyncio
from dotenv import load_dotenv
from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents, DeepgramClientOptions

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("DEEPGRAM_API_KEY")
if not api_key:
    print("ERROR: DEEPGRAM_API_KEY not found in environment variables")
    exit(1)

# Print masked API key for verification
masked_key = api_key[:4] + "*" * (len(api_key) - 4) if len(api_key) > 4 else "****"
print(f"Using Deepgram API key: {masked_key}")

async def main():
    try:
        # Initialize Deepgram client
        config = DeepgramClientOptions(options={"keepalive": "true"})
        deepgram = DeepgramClient(api_key, config)
        
        # Define event handlers
        def on_open(open):
            print(f"Connection opened: {open}")
        
        def on_message(result):
            try:
                transcript = result.channel.alternatives[0].transcript
                if transcript:
                    print(f"Transcript: {transcript}")
            except Exception as e:
                print(f"Error processing transcript: {e}")
        
        def on_error(error):
            print(f"Error: {error}")
        
        def on_close(close):
            print(f"Connection closed: {close}")
        
        # Create connection
        dg_connection = deepgram.listen.live.v("1")
        
        # Register event handlers
        dg_connection.on(LiveTranscriptionEvents.Open, on_open)
        dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
        dg_connection.on(LiveTranscriptionEvents.Error, on_error)
        dg_connection.on(LiveTranscriptionEvents.Close, on_close)
        
        # Define options
        options = LiveOptions(
            model="nova-2",
            language="ko-KR",
            punctuate=True,
            channels=1,
            sample_rate=16000
        )
        
        # Start connection
        print("Starting connection...")
        connection_started = dg_connection.start(options)
        
        if connection_started:
            print("Connection started successfully")
            
            # Wait for a moment to see if connection establishes
            await asyncio.sleep(5)
            
            # Close connection
            print("Closing connection...")
            dg_connection.finish()
            print("Connection closed")
        else:
            print("Failed to start connection")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
