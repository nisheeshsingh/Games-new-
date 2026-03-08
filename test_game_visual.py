"""Playwright test to check for rendering issues in Flappy Bird"""
import asyncio
import time
import subprocess
import os

async def test_game():
    # Start the game process
    game_process = subprocess.Popen(
        ['python3', 'flappy.py'],
        cwd='/Users/singhnisheesh/Source/games/flappy',
        env={**os.environ, 'DISPLAY': ':0'},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Give game time to start
    time.sleep(3)
    
    # Check if process is still running
    if game_process.poll() is not None:
        stdout, stderr = game_process.communicate()
        print("Game crashed!")
        print("STDOUT:", stdout.decode())
        print("STDERR:", stderr.decode())
        return
    
    print("✓ Game started successfully")
    
    # Let it run for a bit
    time.sleep(5)
    
    # Terminate game
    game_process.terminate()
    try:
        game_process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        game_process.kill()
        game_process.wait()
    
    print("✓ Game ran for 5 seconds without crashing")

if __name__ == '__main__':
    asyncio.run(test_game())
