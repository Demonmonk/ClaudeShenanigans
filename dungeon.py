#!/usr/bin/env python3
"""
DUNGEON ESCAPE - A terminal roguelike
Navigate the dungeon, slay monsters, grab treasure, and find the exit!
"""

import random
import os
import sys
import time

# ANSI colors
R = "\033[31m"   # red
G = "\033[32m"   # green
Y = "\033[33m"   # yellow
B = "\033[34m"   # blue
M = "\033[35m"   # magenta
C = "\033[36m"   # cyan
W = "\033[37m"   # white
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

def clear():
    os.system("clear" if os.name == "posix" else "cls")

def pause(msg="Press Enter to continue..."):
    input(f"\n{DIM}{msg}{RESET}")

# ─────────────────────────────────────────────
# WORLD
# ─────────────────────────────────────────────

ROOM_SIZE = 9   # must be odd
DUNGEON_W = 5
DUNGEON_H = 5

TILES = {
    "wall":    "#",
    "floor":   ".",
    "player":  "@",
    "monster": "M",
    "treasure":"$",
    "exit":    "E",
    "stairs":  ">",
}

MONSTERS = [
    {"name": "Goblin",    "hp": 10, "atk": 3,  "xp": 5,  "gold": (1,6),  "symbol": "g"},
    {"name": "Skeleton",  "hp": 15, "atk": 5,  "xp": 8,  "gold": (2,8),  "symbol": "s"},
    {"name": "Orc",       "hp": 25, "atk": 8,  "xp": 15, "gold": (3,12), "symbol": "o"},
    {"name": "Troll",     "hp": 40, "atk": 12, "xp": 25, "gold": (5,20), "symbol": "T"},
    {"name": "Dragon",    "hp": 80, "atk": 20, "xp": 60, "gold": (15,40),"symbol": "D"},
]

ITEMS = [
    {"name": "Health Potion",  "type": "heal",   "value": 20, "symbol": "!"},
    {"name": "Strength Rune",  "type": "attack", "value": 3,  "symbol": "^"},
    {"name": "Shield Charm",   "type": "defense","value": 2,  "symbol": "+"},
]

class Player:
    def __init__(self):
        self.hp = 30
        self.max_hp = 30
        self.atk = 5
        self.defense = 0
        self.gold = 0
        self.xp = 0
        self.level = 1
        self.inventory = []
        self.x = 1
        self.y = 1
        self.floor = 1

    def is_alive(self):
        return self.hp > 0

    def xp_to_next(self):
        return self.level * 20

    def gain_xp(self, amount):
        self.xp += amount
        leveled = False
        while self.xp >= self.xp_to_next():
            self.xp -= self.xp_to_next()
            self.level += 1
            self.max_hp += 10
            self.hp = min(self.hp + 10, self.max_hp)
            self.atk += 2
            leveled = True
        return leveled

    def hp_bar(self):
        pct = self.hp / self.max_hp
        filled = int(pct * 10)
        color = G if pct > 0.5 else Y if pct > 0.25 else R
        bar = color + "█" * filled + DIM + "░" * (10 - filled) + RESET
        return f"[{bar}{color}] {self.hp}/{self.max_hp}{RESET}"


class Monster:
    def __init__(self, template, x, y):
        self.name = template["name"]
        self.hp = template["hp"]
        self.max_hp = template["hp"]
        self.atk = template["atk"]
        self.xp = template["xp"]
        self.gold_range = template["gold"]
        self.symbol = template["symbol"]
        self.x = x
        self.y = y

    def is_alive(self):
        return self.hp > 0

    def color_symbol(self):
        colors = {"g": G, "s": W, "o": Y, "T": R, "D": M}
        return colors.get(self.symbol, W) + BOLD + self.symbol.upper() + RESET


class Dungeon:
    def __init__(self, floor_num, player):
        self.floor = floor_num
        self.width = DUNGEON_W * (ROOM_SIZE + 1) + 1
        self.height = DUNGEON_H * (ROOM_SIZE + 1) + 1
        self.grid = [["#"] * self.width for _ in range(self.height)]
        self.monsters = []
        self.items = []
        self.exit_pos = None
        self._carve_rooms()
        self._place_entities(player)

    def _room_origin(self, rx, ry):
        ox = rx * (ROOM_SIZE + 1) + 1
        oy = ry * (ROOM_SIZE + 1) + 1
        return ox, oy

    def _carve_rooms(self):
        # Carve every room
        for ry in range(DUNGEON_H):
            for rx in range(DUNGEON_W):
                ox, oy = self._room_origin(rx, ry)
                for y in range(ROOM_SIZE):
                    for x in range(ROOM_SIZE):
                        self.grid[oy + y][ox + x] = "."
        # Connect rooms horizontally and vertically
        for ry in range(DUNGEON_H):
            for rx in range(DUNGEON_W):
                ox, oy = self._room_origin(rx, ry)
                if rx < DUNGEON_W - 1:
                    cx = ox + ROOM_SIZE
                    cy = oy + ROOM_SIZE // 2
                    self.grid[cy][cx] = "."
                if ry < DUNGEON_H - 1:
                    cx = ox + ROOM_SIZE // 2
                    cy = oy + ROOM_SIZE
                    self.grid[cy][cx] = "."

    def _random_floor_in_room(self, rx, ry):
        ox, oy = self._room_origin(rx, ry)
        x = ox + random.randint(1, ROOM_SIZE - 2)
        y = oy + random.randint(1, ROOM_SIZE - 2)
        return x, y

    def _place_entities(self, player):
        # Player starts in room (0,0)
        px, py = self._random_floor_in_room(0, 0)
        player.x, player.y = px, py

        # Exit in last room
        ex, ey = self._random_floor_in_room(DUNGEON_W - 1, DUNGEON_H - 1)
        self.exit_pos = (ex, ey)
        self.grid[ey][ex] = "E"

        # Monsters — scale with floor
        occupied = {(px, py), (ex, ey)}
        pool = MONSTERS[: min(2 + self.floor, len(MONSTERS))]
        num_monsters = 5 + self.floor * 2
        for _ in range(num_monsters):
            rx, ry = random.randint(0, DUNGEON_W - 1), random.randint(0, DUNGEON_H - 1)
            if rx == 0 and ry == 0:
                continue
            mx, my = self._random_floor_in_room(rx, ry)
            if (mx, my) not in occupied:
                template = random.choice(pool)
                m = Monster(template, mx, my)
                self.monsters.append(m)
                occupied.add((mx, my))

        # Items
        num_items = 3 + self.floor
        for _ in range(num_items):
            rx, ry = random.randint(0, DUNGEON_W - 1), random.randint(0, DUNGEON_H - 1)
            ix, iy = self._random_floor_in_room(rx, ry)
            if (ix, iy) not in occupied:
                template = random.choice(ITEMS)
                self.items.append({"x": ix, "y": iy, **template})
                occupied.add((ix, iy))

    def monster_at(self, x, y):
        for m in self.monsters:
            if m.is_alive() and m.x == x and m.y == y:
                return m
        return None

    def item_at(self, x, y):
        for item in self.items:
            if item["x"] == x and item["y"] == y:
                return item
        return None

    def remove_item(self, item):
        self.items.remove(item)

    def is_walkable(self, x, y):
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return False
        return self.grid[y][x] != "#"

    def render(self, player, messages):
        VIEWPORT_W = 21
        VIEWPORT_H = 11
        half_w = VIEWPORT_W // 2
        half_h = VIEWPORT_H // 2
        cam_x = player.x
        cam_y = player.y

        lines = []
        for dy in range(-half_h, half_h + 1):
            row = ""
            for dx in range(-half_w, half_w + 1):
                wx = cam_x + dx
                wy = cam_y + dy
                if wx == player.x and wy == player.y:
                    row += f"{Y}{BOLD}@{RESET}"
                    continue
                m = self.monster_at(wx, wy)
                if m:
                    row += m.color_symbol()
                    continue
                item = self.item_at(wx, wy)
                if item:
                    row += f"{C}{item['symbol']}{RESET}"
                    continue
                if wx < 0 or wy < 0 or wx >= self.width or wy >= self.height:
                    row += " "
                else:
                    tile = self.grid[wy][wx]
                    if tile == "#":
                        row += f"{DIM}#{RESET}"
                    elif tile == "E":
                        row += f"{G}{BOLD}E{RESET}"
                    else:
                        row += f"{DIM}.{RESET}"
            lines.append(row)

        # Stats panel
        xp_bar_len = 10
        xp_pct = player.xp / player.xp_to_next()
        xp_filled = int(xp_pct * xp_bar_len)
        xp_bar = C + "▪" * xp_filled + DIM + "·" * (xp_bar_len - xp_filled) + RESET

        stats = [
            f"{BOLD}{M}╔══ DUNGEON ESCAPE ══╗{RESET}",
            f" Floor {B}{player.floor}{RESET}  |  {Y}${player.gold}{RESET} gold",
            f" HP   {player.hp_bar()}",
            f" LVL  {M}{player.level}{RESET}  XP [{xp_bar}]",
            f" ATK  {R}{player.atk}{RESET}  DEF {B}{player.defense}{RESET}",
            f"{BOLD}{M}╠══ MESSAGES ════════╣{RESET}",
        ]
        for msg in messages[-4:]:
            stats.append(" " + msg)
        while len(stats) < 10:
            stats.append("")
        stats.append(f"{BOLD}{M}╠══ CONTROLS ════════╣{RESET}")
        stats.append(f" {W}WASD{RESET}/{W}↑↓←→{RESET} move  {W}I{RESET} items")
        stats.append(f" {W}Q{RESET} quit")
        stats.append(f"{BOLD}{M}╚════════════════════╝{RESET}")

        # Combine map + stats side by side
        map_lines = lines
        print()
        for i, row in enumerate(map_lines):
            side = stats[i] if i < len(stats) else ""
            print(f"  {row}   {side}")
        if len(stats) > len(map_lines):
            for s in stats[len(map_lines):]:
                print(f"  {'':>{VIEWPORT_W * 2}}   {s}")


# ─────────────────────────────────────────────
# COMBAT
# ─────────────────────────────────────────────

def combat(player, monster, messages):
    messages.append(f"{R}⚔  You engage the {monster.name}!{RESET}")
    while player.is_alive() and monster.is_alive():
        # Player attacks
        dmg = max(1, player.atk - random.randint(0, 2))
        monster.hp -= dmg
        messages.append(f"  {G}You hit {monster.name} for {dmg} dmg{RESET} (hp:{max(0,monster.hp)})")
        if not monster.is_alive():
            gold = random.randint(*monster.gold_range)
            player.gold += gold
            leveled = player.gain_xp(monster.xp)
            messages.append(f"  {Y}★ {monster.name} slain! +{monster.xp}xp +{gold}g{RESET}")
            if leveled:
                messages.append(f"  {M}{BOLD}LEVEL UP! Now level {player.level}!{RESET}")
            return True

        # Monster attacks
        mdmg = max(1, monster.atk - player.defense - random.randint(0, 2))
        player.hp -= mdmg
        messages.append(f"  {R}{monster.name} hits you for {mdmg} dmg{RESET} (hp:{max(0,player.hp)})")
        if not player.is_alive():
            messages.append(f"  {R}{BOLD}You have been slain!{RESET}")
            return False
    return False


# ─────────────────────────────────────────────
# INVENTORY / ITEM USE
# ─────────────────────────────────────────────

def show_inventory(player, messages):
    clear()
    print(f"\n{BOLD}{M}=== INVENTORY ==={RESET}\n")
    if not player.inventory:
        print(f"  {DIM}(empty){RESET}")
    else:
        for i, item in enumerate(player.inventory):
            print(f"  {C}{i+1}{RESET}. {item['name']}")
    print(f"\n  Gold: {Y}{player.gold}{RESET}")
    print(f"\nEnter item number to use, or 0 to cancel: ", end="")
    choice = input().strip()
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(player.inventory):
            use_item(player, player.inventory[idx], messages)
            player.inventory.pop(idx)


def use_item(player, item, messages):
    if item["type"] == "heal":
        healed = min(item["value"], player.max_hp - player.hp)
        player.hp += healed
        messages.append(f"{G}Used {item['name']}: healed {healed} HP{RESET}")
    elif item["type"] == "attack":
        player.atk += item["value"]
        messages.append(f"{R}Used {item['name']}: +{item['value']} ATK permanently!{RESET}")
    elif item["type"] == "defense":
        player.defense += item["value"]
        messages.append(f"{B}Used {item['name']}: +{item['value']} DEF permanently!{RESET}")


# ─────────────────────────────────────────────
# MAIN GAME LOOP
# ─────────────────────────────────────────────

MOVES = {
    "w": (0, -1), "a": (-1, 0), "s": (0, 1), "d": (1, 0),
    "\x1b[A": (0, -1), "\x1b[B": (0, 1), "\x1b[D": (-1, 0), "\x1b[C": (1, 0),
}

def get_key():
    """Read a single keypress."""
    import tty, termios
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            ch2 = sys.stdin.read(1)
            if ch2 == "[":
                ch3 = sys.stdin.read(1)
                return "\x1b[" + ch3
            return ch
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def title_screen():
    clear()
    art = f"""
{M}{BOLD}
  ██████╗ ██╗   ██╗███╗   ██╗ ██████╗ ███████╗ ██████╗ ███╗   ██╗
  ██╔══██╗██║   ██║████╗  ██║██╔════╝ ██╔════╝██╔═══██╗████╗  ██║
  ██║  ██║██║   ██║██╔██╗ ██║██║  ███╗█████╗  ██║   ██║██╔██╗ ██║
  ██║  ██║██║   ██║██║╚██╗██║██║   ██║██╔══╝  ██║   ██║██║╚██╗██║
  ██████╔╝╚██████╔╝██║ ╚████║╚██████╔╝███████╗╚██████╔╝██║ ╚████║
  ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝
{RESET}
{Y}  ███████╗███████╗ ██████╗ █████╗ ██████╗ ███████╗{RESET}
{Y}  ██╔════╝██╔════╝██╔════╝██╔══██╗██╔══██╗██╔════╝{RESET}
{Y}  █████╗  ███████╗██║     ███████║██████╔╝█████╗  {RESET}
{Y}  ██╔══╝  ╚════██║██║     ██╔══██║██╔═══╝ ██╔══╝  {RESET}
{Y}  ███████╗███████║╚██████╗██║  ██║██║     ███████╗{RESET}
{Y}  ╚══════╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝     ╚══════╝{RESET}
"""
    print(art)
    print(f"  {W}Navigate 5 dungeon floors and escape with your life!{RESET}")
    print(f"\n  {DIM}Monsters:  {G}g{RESET}oblin  {W}S{RESET}keleton  {Y}O{RESET}rc  {R}T{RESET}roll  {M}D{RESET}ragon{RESET}")
    print(f"  {DIM}Items:     {C}!{RESET} potion  {C}^{RESET} rune  {C}+{RESET} charm{RESET}")
    print(f"  {DIM}Exit:      {G}E{RESET} = stairs to next floor (final floor = escape!){RESET}")
    print(f"\n  {BOLD}Move with WASD. Bump into monsters to fight. Walk over items to pick up.{RESET}")
    pause("  Press Enter to descend into the dungeon...")


def death_screen(player):
    clear()
    print(f"""
{R}{BOLD}
  ██╗   ██╗ ██████╗ ██╗   ██╗    ██████╗ ██╗███████╗██████╗
  ╚██╗ ██╔╝██╔═══██╗██║   ██║    ██╔══██╗██║██╔════╝██╔══██╗
   ╚████╔╝ ██║   ██║██║   ██║    ██║  ██║██║█████╗  ██║  ██║
    ╚██╔╝  ██║   ██║██║   ██║    ██║  ██║██║██╔══╝  ██║  ██║
     ██║   ╚██████╔╝╚██████╔╝    ██████╔╝██║███████╗██████╔╝
     ╚═╝    ╚═════╝  ╚═════╝     ╚═════╝ ╚═╝╚══════╝╚═════╝
{RESET}""")
    print(f"  You reached floor {B}{player.floor}{RESET}, level {M}{player.level}{RESET}, with {Y}{player.gold}{RESET} gold.")
    pause()


def victory_screen(player):
    clear()
    print(f"""
{G}{BOLD}
  ██╗   ██╗██╗ ██████╗████████╗ ██████╗ ██████╗ ██╗   ██╗██╗
  ██║   ██║██║██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗╚██╗ ██╔╝██║
  ██║   ██║██║██║        ██║   ██║   ██║██████╔╝ ╚████╔╝ ██║
  ╚██╗ ██╔╝██║██║        ██║   ██║   ██║██╔══██╗  ╚██╔╝  ╚═╝
   ╚████╔╝ ██║╚██████╗   ██║   ╚██████╔╝██║  ██║   ██║   ██╗
    ╚═══╝  ╚═╝ ╚═════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝
{RESET}""")
    print(f"  {BOLD}You escaped the dungeon!{RESET}")
    print(f"\n  Final stats:")
    print(f"    Floor: {B}5{RESET}  |  Level: {M}{player.level}{RESET}  |  Gold: {Y}{player.gold}{RESET}")
    print(f"    Attack: {R}{player.atk}{RESET}  |  Defense: {B}{player.defense}{RESET}")
    pause()


def game_loop():
    player = Player()
    MAX_FLOOR = 5

    for floor_num in range(1, MAX_FLOOR + 1):
        player.floor = floor_num
        dungeon = Dungeon(floor_num, player)
        messages = [f"{C}Floor {floor_num}: Descend deeper...{RESET}"]

        running = True
        while running:
            clear()
            dungeon.render(player, messages)

            key = get_key()

            if key in ("q", "Q", "\x03"):
                print(f"\n{DIM}Farewell, brave adventurer.{RESET}\n")
                return

            if key in ("i", "I"):
                show_inventory(player, messages)
                continue

            if key not in MOVES:
                continue

            dx, dy = MOVES[key]
            nx, ny = player.x + dx, player.y + dy

            if not dungeon.is_walkable(nx, ny):
                messages.append(f"{DIM}A wall blocks your path.{RESET}")
                continue

            # Check monster
            monster = dungeon.monster_at(nx, ny)
            if monster:
                alive = combat(player, monster, messages)
                if not alive:
                    clear()
                    dungeon.render(player, messages)
                    time.sleep(1)
                    death_screen(player)
                    return
                continue

            # Move player
            player.x, player.y = nx, ny

            # Check item
            item = dungeon.item_at(nx, ny)
            if item:
                player.inventory.append(item)
                dungeon.remove_item(item)
                messages.append(f"{C}Picked up {item['name']}! (use with I){RESET}")

            # Check exit
            if dungeon.grid[ny][nx] == "E":
                if floor_num == MAX_FLOOR:
                    clear()
                    dungeon.render(player, messages)
                    time.sleep(0.5)
                    victory_screen(player)
                    return
                else:
                    messages = [f"{G}★ You descend to floor {floor_num + 1}!{RESET}"]
                    running = False  # next floor


def main():
    while True:
        title_screen()
        game_loop()
        print(f"\n{Y}Play again? (y/n): {RESET}", end="")
        ans = input().strip().lower()
        if ans != "y":
            print(f"\n{DIM}Thanks for playing Dungeon Escape!{RESET}\n")
            break


if __name__ == "__main__":
    main()
