#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os
import random
import time
from datetime import datetime
import subprocess
from subprocess import run, PIPE, DEVNULL
import argparse
import hashlib
import getpass
import json
import sys

def get_password_hash(password):
    salt = b'ml_lock_salt'
    return hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    ).hex()

def set_password():
    config_dir = os.path.expanduser('~/.config/ml_lock')
    os.makedirs(config_dir, exist_ok=True)
    
    while True:
        password = getpass.getpass('Enter new password: ')
        confirm = getpass.getpass('Confirm password: ')
        
        if password == confirm:
            password_hash = get_password_hash(password)
            with open(os.path.join(config_dir, 'config.json'), 'w') as f:
                json.dump({'password_hash': password_hash}, f)
            print('Password set successfully')
            return
        print('Passwords do not match. Try again.')

class LockScreen:
    def __init__(self):
        config_path = os.path.expanduser('~/.config/ml_lock/config.json')
        try:
            with open(config_path) as f:
                config = json.load(f)
                self.password_hash = config['password_hash']
        except (FileNotFoundError, KeyError):
            print("No password set. Please run with -p to set a password first.")
            sys.exit(1)

        self.root = tk.Tk()
        self.root.title("ML Lock")
        
        self.is_wayland = 'WAYLAND_DISPLAY' in os.environ
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        self.root.configure(background='black')
        self.root.geometry(f"{screen_width}x{screen_height}+0+0")
        
        self.root.overrideredirect(True)
        
        if self.is_wayland:
            self.root.wait_visibility()
            self.root.attributes('-fullscreen', True)
        else:
            self.root.attributes('-fullscreen', True, '-topmost', True)
            self.root.wm_attributes('-type', 'splash')
            self.check_top_most()
        
        self.root.focus_force()
        self.root.lift()
        
        img_path = self.get_random_image()
        self.display_image(img_path)
        
        self.overlay_frame = tk.Canvas(
            self.root,
            highlightthickness=0,
            bg='black'
        )
        self.overlay_frame.place(relx=0.5, rely=0.9, anchor="center", width=400, height=120)
        
        self.overlay_frame.create_rectangle(
            0, 0, 400, 120,
            fill='black',
            stipple='gray25',
            width=0
        )

        self.overlay_frame.create_rectangle(
            2, 2, 398, 118,
            outline='#333333',
            width=1
        )

        self.start_time = datetime.now()

        self.style = ttk.Style()
        self.style.configure(
            'Modern.TEntry',
            fieldbackground='#2a2a2a',
            foreground='white',
            insertcolor='white',
            borderwidth=0,
            relief='flat'
        )
        
        self.style.configure(
            'Modern.TLabel',
            background='black',
            foreground='#ffffff',
            font=('Helvetica', 16, 'bold')
        )

        self.overlay_frame.create_rectangle(
            50, 20, 350, 60,
            fill='#2a2a2a',
            outline='#3a3a3a',
            width=1
        )

        self.countdown_active = False
        self.countdown_seconds = 0
        self.entry_window = None
        
        self.password_var = tk.StringVar()
        self.entry = ttk.Entry(
            self.overlay_frame,
            show="•",
            textvariable=self.password_var,
            style='Modern.TEntry',
            width=30
        )
        self.entry_window = self.overlay_frame.create_window(200, 40, window=self.entry)
        
        self.timer_label = ttk.Label(
            self.overlay_frame,
            style='Modern.TLabel'
        )
        self.overlay_frame.create_window(200, 90, window=self.timer_label)
        
        self.check_focus()
        
        self.root.bind('<Escape>', lambda e: "break")
        self.root.bind('<Return>', self.check_password)
        
        self.root.bind('<Control-q>', lambda e: "break")
        self.root.bind('<Control-w>', lambda e: "break")
        self.root.bind('<Alt-F4>', lambda e: "break")
        self.root.bind('<Alt-Tab>', lambda e: "break")
        
        self.root.bind('<Button-1>', lambda e: None)
        self.root.bind('<Button-2>', lambda e: None)
        self.root.bind('<Button-3>', lambda e: None)
        
        self.root.bind('<Alt_L>', lambda e: "break")
        self.root.bind('<Alt_R>', lambda e: "break")
        self.root.bind('<Super_L>', lambda e: "break")
        self.root.bind('<Super_R>', lambda e: "break")
        
        self.root.bind('<Key>', self.handle_key)
        
        self.update_timer()
        
        self.correct_password = "123"
        
        self.root.after(100, self.setup_security)
        
        self.disable_gnome_overview()
        
        if self.is_wayland:
            self.root.attributes('-type', 'dock')
            self.root.attributes('-fullscreen', True)
            self.disable_shortcuts()
        
    def check_top_most(self):
        """Periodically ensure window stays on top (X11 only)"""
        if not self.is_wayland:
            self.root.lift()
            self.root.attributes('-topmost', True)
            self.root.after(500, self.check_top_most)
        
    def setup_security(self):
        try:
            self.root.grab_set_global()
            self.entry.focus_force()
            
            if not self.is_wayland:
                try:
                    subprocess.run(['wmctrl', '-i', '-r', str(self.root.winfo_id()), '-b', 'add,sticky,above,fullscreen'], check=False)
                except:
                    pass
            else:
                self.root.attributes('-fullscreen', True)
                self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")
                
        except Exception as e:
            print(f"Warning: Could not set up all security measures: {e}")
        
        self.root.lift()
        self.entry.focus_force()
        self.root.after(100, self.check_fullscreen)

    def check_fullscreen(self):
        if not self.root.attributes('-fullscreen'):
            self.root.attributes('-fullscreen', True)
        self.root.lift()
        self.entry.focus_force()
        self.root.after(500, self.check_fullscreen)

    def check_focus(self):
        if self.root.focus_get() != self.entry:
            self.entry.focus_force()
        self.root.after(100, self.check_focus)

    def handle_key(self, event):
        if event.keysym in ('Return', 'BackSpace', 'Delete', 'Tab'):
            return
        if len(event.char) == 0:
            return "break"
        return

    def cleanup_and_quit(self):
        try:
            self.root.grab_release()
            self.enable_gnome_overview()
        except:
            pass
        self.root.quit()

    def get_random_image(self):
        img_folder = os.path.join(os.path.dirname(__file__), 'img')
        images = [f for f in os.listdir(img_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        return os.path.join(img_folder, random.choice(images))
    
    def display_image(self, img_path):
        image = Image.open(img_path)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        width_ratio = screen_width / image.width
        height_ratio = screen_height / image.height
        scale = max(width_ratio, height_ratio)
        
        new_width = int(image.width * scale)
        new_height = int(image.height * scale)
        
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(image)
        
        label = tk.Label(self.root, image=photo, background="black")
        label.image = photo
        label.place(x=(screen_width-new_width)//2, y=(screen_height-new_height)//2)
    
    def update_timer(self):
        elapsed = datetime.now() - self.start_time
        hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        timer_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        self.timer_label.config(
            text=f"{timer_text}",
            foreground='#ffffff'
        )
        self.root.after(1000, self.update_timer)
    
    def start_countdown(self):
        if self.countdown_seconds > 0:
            self.overlay_frame.delete(self.entry_window)
            self.countdown_seconds -= 1
            self.root.after(1000, self.start_countdown)
        else:
            self.countdown_active = False
            self.entry_window = self.overlay_frame.create_window(200, 40, window=self.entry)
            self.entry.focus_force()

    def check_password(self, event=None):
        if self.countdown_active:
            return "break"
            
        entered_hash = get_password_hash(self.password_var.get())
        if entered_hash == self.password_hash:
            self.cleanup_and_quit()
        else:
            self.password_var.set("")
            self.countdown_active = True
            self.countdown_seconds = 3
            self.start_countdown()
        return "break"

    def run(self):
        self.root.mainloop()

    def disable_gnome_overview(self):
        try:
            run(['gsettings', 'set', 'org.gnome.mutter', 'overlay-key', ''], stdout=DEVNULL, stderr=DEVNULL)
            run(['gsettings', 'set', 'org.gnome.desktop.interface', 'enable-hot-corners', 'false'], stdout=DEVNULL, stderr=DEVNULL)
        except Exception:
            pass

    def enable_gnome_overview(self):
        """Re-enable GNOME shell overview"""
        try:
            run(['gsettings', 'reset', 'org.gnome.mutter', 'overlay-key'], stdout=DEVNULL, stderr=DEVNULL)
            run(['gsettings', 'reset', 'org.gnome.desktop.interface', 'enable-hot-corners'], stdout=DEVNULL, stderr=DEVNULL)
        except Exception:
            pass

    def disable_shortcuts(self):
        """Disable various desktop environment shortcuts"""
        try:
            run(['gsettings', 'set', 'org.gnome.desktop.wm.keybindings', 'switch-to-workspace-up', '[]'], stdout=DEVNULL, stderr=DEVNULL)
            run(['gsettings', 'set', 'org.gnome.desktop.wm.keybindings', 'switch-to-workspace-down', '[]'], stdout=DEVNULL, stderr=DEVNULL)
            run(['gsettings', 'set', 'org.gnome.desktop.wm.keybindings', 'switch-applications', '[]'], stdout=DEVNULL, stderr=DEVNULL)
            run(['gsettings', 'set', 'org.gnome.desktop.wm.keybindings', 'switch-windows', '[]'], stdout=DEVNULL, stderr=DEVNULL)
        except Exception:
            pass

def main():
    parser = argparse.ArgumentParser(description='ML Lock - Modern Linux Lock Screen')
    parser.add_argument('-p', '--set-password', action='store_true',
                       help='Set a new password')
    args = parser.parse_args()

    if args.set_password:
        set_password()
    else:
        lock_screen = LockScreen()
        lock_screen.run()

if __name__ == "__main__":
    main()
