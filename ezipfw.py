#!/usr/bin/env python3
from blessed import Terminal
import subprocess
import sys
from typing import List, Dict

class IpfwTUI:
    def __init__(self):
        self.term = Terminal()
        self.current_rules = []
        self.selected_index = 0
        self.command_mode = False
        self.command_string = ""
        self.status_message = ""
        self.scroll_offset = 0
        self.command_history = []
        self.history_index = 0

    def get_ipfw_rules(self) -> List[Dict]:
        try:
            output = subprocess.check_output(["ipfw", "list"]).decode()
            rules = []
            for line in output.split('\n'):
                if line.strip():
                    parts = line.split(maxsplit=1)
                    if len(parts) >= 2:
                        rules.append({
                            'number': parts[0],
                            'rule': parts[1]
                        })
            return rules
        except subprocess.CalledProcessError:
            return []

    def draw_screen(self):
        print(self.term.clear())
        
        # Calculate available space
        available_height = self.term.height - 6  # Space for header, footer, status, command
        
        # Draw title
        title = "IPFW Configuration TUI"
        print(self.term.move_xy((self.term.width - len(title)) // 2, 0) + 
              self.term.bold + title + self.term.normal)
        
        # Draw help text
        help_text = "↑/↓: Navigate | a: Add | d: Delete | e: Edit | q: Quit | /: Search"
        print(self.term.move_xy((self.term.width - len(help_text)) // 2, 1) + help_text)
        
        # Draw rules
        visible_rules = self.current_rules[self.scroll_offset:self.scroll_offset + available_height]
        for idx, rule in enumerate(visible_rules):
            screen_idx = idx + 3  # Start after title and help
            if screen_idx >= self.term.height - 3:
                break
                
            display_text = f"{rule['number']}: {rule['rule']}"
            if len(display_text) > self.term.width - 2:
                display_text = display_text[:self.term.width-5] + "..."
                
            if idx + self.scroll_offset == self.selected_index:
                print(self.term.move_xy(1, screen_idx) + 
                      self.term.reverse + display_text + self.term.normal)
            else:
                print(self.term.move_xy(1, screen_idx) + display_text)
        
        # Draw scroll indicator if needed
        if len(self.current_rules) > available_height:
            progress = self.scroll_offset / (len(self.current_rules) - available_height)
            indicator_pos = int(progress * (available_height - 1))
            for i in range(available_height):
                char = '█' if i == indicator_pos else '│'
                print(self.term.move_xy(self.term.width - 1, i + 3) + char)
        
        # Draw status message
        if self.status_message:
            print(self.term.move_xy(1, self.term.height-2) + 
                  self.term.bold + self.status_message + self.term.normal)
        
        # Draw command line
        if self.command_mode:
            prompt = "Command: "
            print(self.term.move_xy(1, self.term.height-1) + prompt + self.command_string)
            print(self.term.move_xy(len(prompt) + len(self.command_string) + 1, 
                  self.term.height-1), end='', flush=True)

    def execute_ipfw_command(self, command: str) -> bool:
        try:
            subprocess.run(["ipfw"] + command.split(), check=True)
            if command.strip():
                self.command_history.append(command)
            return True
        except subprocess.CalledProcessError:
            return False

    def handle_command_input(self, key):
        if key.code == self.term.KEY_ENTER:
            if self.execute_ipfw_command(self.command_string):
                self.status_message = "Command executed successfully"
            else:
                self.status_message = "Error executing command"
            self.command_mode = False
            self.command_string = ""
            return True
        elif key.code == self.term.KEY_ESCAPE:
            self.command_mode = False
            self.command_string = ""
            return True
        elif key.code == self.term.KEY_BACKSPACE:
            self.command_string = self.command_string[:-1]
        elif key.code == self.term.KEY_UP and self.command_history:
            if self.history_index > 0:
                self.history_index -= 1
                self.command_string = self.command_history[self.history_index]
        elif key.code == self.term.KEY_DOWN and self.command_history:
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.command_string = self.command_history[self.history_index]
        elif not key.code:  # Regular character
            self.command_string += key
        return False

    def run(self):
        with self.term.fullscreen(), self.term.cbreak(), self.term.hidden_cursor():
            while True:
                self.current_rules = self.get_ipfw_rules()
                self.draw_screen()
                
                key = self.term.inkey()
                
                if self.command_mode:
                    if self.handle_command_input(key):
                        continue
                else:
                    if key.lower() == 'q':
                        break
                    elif key.code == self.term.KEY_UP:
                        if self.selected_index > 0:
                            self.selected_index -= 1
                            if self.selected_index < self.scroll_offset:
                                self.scroll_offset = self.selected_index
                    elif key.code == self.term.KEY_DOWN:
                        if self.selected_index < len(self.current_rules) - 1:
                            self.selected_index += 1
                            if self.selected_index >= self.scroll_offset + (self.term.height - 6):
                                self.scroll_offset += 1
                    elif key.lower() == 'a':
                        self.command_mode = True
                        self.command_string = ""
                        self.history_index = len(self.command_history)
                    elif key.lower() == 'd':
                        if self.current_rules:
                            rule_num = self.current_rules[self.selected_index]['number']
                            if self.execute_ipfw_command(f"delete {rule_num}"):
                                self.status_message = f"Deleted rule {rule_num}"
                            else:
                                self.status_message = "Error deleting rule"
                    elif key.lower() == 'e' and self.current_rules:
                        rule = self.current_rules[self.selected_index]
                        self.command_mode = True
                        self.command_string = f"delete {rule['number']} && add {rule['rule']}"
                        self.history_index = len(self.command_history)

                if not self.command_mode:
                    self.status_message = ""

def main():
    if sys.platform != "freebsd":
        print("This script is intended for FreeBSD systems with IPFW installed.")
        sys.exit(1)
        
    try:
        tui = IpfwTUI()
        tui.run()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
