import sys
import os
import shutil
import re
import filecmp

import sqlite3

import argparse

#sprites_folder = "Graphics/CustomBattlers/indexed/"
		
class sprite_hybridizer:
	def __init__(self, pokemon_1 = None, pokemon_2 = None, custom_dir = "Graphics/CustomBattlers/indexed/"):
		self.base_dir = custom_dir
		
		self.pokemon_1 = pokemon_1
		self.pokemon_2 = pokemon_2
		self.p1_index = None
		self.p2_index = None
		self.existing_p1_combos = None
		self.existing_p2_combos = None
		
		self.log_file = "hybridized_pokemon_list.sqlite3.db"
		#self.log_file = "hybridized_pokemon_list.txt"
		self.hybridization_log = []
		self.hybridized_log_connection = None
		self.hybridized_log_cursor = None
		
		self.pokedex = pokedex()
		
	def opendb(self):
		if self.hybridized_log_connection is None:
			self.hybridized_log_connection = sqlite3.connect(self.log_file)
			self.hybridized_log_cursor = self.hybridized_log_connection.cursor()
			
	def closedb(self):
		if self.hybridized_log_connection is not None:
			self.hybridized_log_cursor.close()
			self.hybridized_log_connection.close()
			self.hybridized_log_cursor = None
			self.hybridized_log_connection = None
		
	def initialize_db(self):
		schema = "CREATE TABLE IF NOT EXISTS changelog (modified_file TEXT PRIMARY KEY, head_fusion TEXT, body_fusion TEXT, as_pokemon TEXT, dex_no INTEGER)"
		self.hybridized_log_cursor.execute(schema)
		self.hybridized_log_connection.commit()
		
		
	def collect_indexes(self):
		if self.pokemon_1 not in self.pokedex.name_to_num:
			print("Pokemon:", self.pokemon_1, "not recognized!")
		if self.pokemon_2 not in self.pokedex.name_to_num:
			print("Pokemon:", self.pokemon_2, "not recognized!")
		if self.pokemon_1 in self.pokedex.name_to_num and self.pokemon_2 in self.pokedex.name_to_num:
			self.p1_index = self.pokedex.name_to_num[self.pokemon_1]
			self.p2_index = self.pokedex.name_to_num[self.pokemon_2]
		else:
			self.p1_index = None
			self.p2_index = None
	
	def collect_dir(self, base, index_pair):
		target = os.path.normpath(self.base_dir + "/" + base)
		existing_sprites = os.listdir(target)
		#find_exist_pattern = index_pair+"[a-z]?\.png"
		find_exist_pattern = index_pair+"([a-z]*)\.png"
		#existing_variants = [hb for hb in existing_sprites if re.match(find_exist_pattern, hb)]
		existing_variants = [hb for hb in existing_sprites if re.match(find_exist_pattern, hb)]
		#No sprite for this fusion exists
		if len(existing_variants) == 0:
			existing_variants = []
			next_letter = ""
		else:
			find_exist_letters = "\d+\.\d+([a-z]*).png"
			existing_letters = [re.findall(find_exist_letters, s)[0] for s in existing_variants]
			next_letter = existing_letters[len(existing_letters)-1]
			next_letter = self.get_next_letter(next_letter)
			
		return existing_variants, next_letter
	
	def sprite_is_new(self, sprite_to_add, existing_sprites, exist_dir):
		sprite_already_exists = [filecmp.cmp(os.path.normpath(self.base_dir + "/"+ sprite_to_add), os.path.normpath(self.base_dir + "/" + exist_dir + "/"+ exist), shallow = False) for exist in existing_sprites]
		same_sprite = not any(sprite_already_exists)
		if not same_sprite and len(existing_sprites) > 0:
			represented_as = [i for i, x in enumerate(sprite_already_exists) if x]
			represented_as = represented_as[0]
			represented_as = existing_sprites[represented_as]
		else:
			represented_as = None
			
		return same_sprite, represented_as
	
	def get_next_letter(self, current_letter):
		next_letter = []
		if len(current_letter) == 0:
			next_letter = "a"
		else:
			#allow for an arbitrary number of alts
			if current_letter.endswith("z"):
				next_letter = "".join(["a"]*(len(current_letter)+1))
			else:
				if len(current_letter) == 1:
					next_letter = chr(ord(current_letter)+1)
				else:
					last_letter = current_letter[len(current_letter)-1]
					new_last_letter = chr(ord(last_letter)+1)
					next_letter = current_letter[(len(current_letter)-1):]
					next_letter+= new_last_letter
				
		return next_letter
	
	def hybridize_pair(self):
		if self.p1_index is not None and self.p2_index is not None:
			head = str(self.p1_index)
			body = str(self.p2_index)
			
			head_body = head+"."+body
			body_head = body+"."+head
			
			heads, next_head_letter = self.collect_dir(head, head_body)
			bodies, next_body_letter = self.collect_dir(body, body_head)
			
			moves_to_make = []
			for sprite in bodies:
				from_sprite = body+"/"+sprite
				to_sprite = head+"/"+head_body+next_head_letter+".png"
				next_move = [from_sprite, to_sprite]
				
				new_sprite, or_already_exists_as = self.sprite_is_new(from_sprite, heads, head)
				if new_sprite:
					next_head_letter = self.get_next_letter(next_head_letter)

					moves_to_make.append(next_move)
				else:
					print(from_sprite, "already exists as an alternative in", head, "as", or_already_exists_as, "and will not be copied.")
					
			for sprite in heads:
				from_sprite = head+"/"+sprite
				to_sprite = body+"/"+body_head+next_body_letter+".png"
				new_sprite, or_already_exists_as = self.sprite_is_new(from_sprite, bodies, body)
				if new_sprite:
					next_move = [from_sprite, to_sprite]
					next_body_letter = self.get_next_letter(next_body_letter)
						
					moves_to_make.append(next_move)
					
				else:
					print(from_sprite, "already exists as an alternative in", body, "as", or_already_exists_as, "and will not be copied.")
					
					
			for m in moves_to_make:
				print("Copying", m[0], "to", m[1])
				self.hybridization_log.append(m)
				shutil.copy(os.path.normpath(self.base_dir + "/" + m[0]), os.path.normpath(self.base_dir + "/" + m[1]))
		
			self.log_to_sql()
	
	
	'''
	'''
	def add_other_evols(self):
		if self.p1_index is not None and self.p2_index is not None:
			target_head = str(self.p1_index)
			body = str(self.p2_index)
			
			#move_target = os.path.normpath(self.base_dir + "/" + target_head + "/" + target_head + "." + body + "{variant}.png")
			move_target = os.path.normpath(target_head + "/" + target_head + "." + body + "{variant}.png")
			
			existing_target_sprites, next_letter = self.collect_dir(target_head, target_head+"."+body)
	
			head_evos = self.pokedex.relationships[self.pokemon_1]
			body_evos = self.pokedex.relationships[self.pokemon_2]
			
			head_indices = [str(self.pokedex.name_to_num[evo]) for evo in head_evos]
			body_indices = [str(self.pokedex.name_to_num[evo]) for evo in body_evos]
			head_indices.append(target_head)
			body_indices.append(body)
			
			moves_to_make = []	
			for h in head_indices:
				for b in body_indices:
					hb = h+"."+b
					bh = b+"."+h
					
					head_body_sprites, trash = self.collect_dir(h, hb)
					body_head_sprites, trash = self.collect_dir(b, bh)
					head_body_sprites = [os.path.normpath(h+"/"+s) for s in head_body_sprites]
					body_head_sprites = [os.path.normpath(b+"/"+s) for s in body_head_sprites]
					
					for from_sprite in head_body_sprites:
						to_sprite = move_target
						to_sprite = move_target.format(variant = next_letter)
						new_sprite, or_already_exists_as = self.sprite_is_new(from_sprite, existing_target_sprites, target_head)
						if new_sprite:
							next_move = [from_sprite, to_sprite]
							next_letter = self.get_next_letter(next_letter)
						
							moves_to_make.append(next_move)
						else:
							print(from_sprite, "already exists as an alternative in", target_head, "as", or_already_exists_as, "and will not be copied.")
						
					for from_sprite in body_head_sprites:
						to_sprite = move_target
						to_sprite = move_target.format(variant = next_letter)
						new_sprite, or_already_exists_as = self.sprite_is_new(from_sprite, existing_target_sprites, target_head)
						if new_sprite:
							next_move = [from_sprite, to_sprite]
							if len(next_letter) == 0:
								next_letter = "a"
							else:
								next_letter = chr(ord(next_letter)+1)
						
							moves_to_make.append(next_move)
						else:
							print(from_sprite, "already exists as an alternative in", target_head, "as", or_already_exists_as, "and will not be copied.")
						
			for m in moves_to_make:
				print("Copying", m[0], "to", m[1])
				self.hybridization_log.append(m)
				shutil.copy(os.path.normpath(self.base_dir + "/" + m[0]), os.path.normpath(self.base_dir + "/" + m[1]))
		
			self.log_to_sql()
		
	def log_to_sql(self):
		prefix = "^(\d+)\.(\d+)"
		insertions = []
		for sprite_pair in self.hybridization_log:
			from_sprite = os.path.normpath(self.base_dir + "/" +os.path.basename(sprite_pair[0]))
			to_sprite = os.path.normpath(self.base_dir + "/" +sprite_pair[1])
			
			head_body = re.findall(prefix, os.path.basename(sprite_pair[0]))[0]
			head_fuse = self.pokedex.num_to_name[int(head_body[0])]
			body_fuse = self.pokedex.num_to_name[int(head_body[1])]
			
			to_breakdown = re.findall(prefix, os.path.basename(sprite_pair[1]))[0]
			
			as_pok_idx = int(to_breakdown[0])
			as_pokemon = self.pokedex.num_to_name[as_pok_idx]
			
			next_row = (to_sprite, head_fuse, body_fuse, as_pokemon, as_pok_idx,)
			insertions.append(next_row)
		
		self.opendb()
		self.initialize_db()
		self.hybridized_log_cursor.executemany("INSERT OR IGNORE INTO changelog VALUES (?, ?, ?, ?, ?)", insertions)
		self.hybridized_log_connection.commit()
		self.closedb()
			
	def restore_from_log(self, revert_pokemon):
		sql = "SELECT * FROM changelog WHERE as_pokemon=?"
		cleanup = "DELETE FROM changelog WHERE as_pokemon=?"
		
		if os.path.exists(self.log_file):
			self.opendb()
			try:
				files = self.hybridized_log_cursor.execute(sql, (revert_pokemon, )).fetchall()
				if len(files) == 0:
					print("It looks like you haven't altered any files for", revert_pokemon, "with me yet!")
					print("There are no changes to revert.")
				
				for f in files:
					delete_me = os.path.normpath(f[0])
					if os.path.exists(delete_me):
						print("Removing", delete_me)
						os.remove(delete_me)
					else:
						print("Couldn't find", delete_me, "skipping it.")
				
				self.hybridized_log_cursor.execute(cleanup, (revert_pokemon, ))
				self.hybridized_log_connection.commit()
				
				self.closedb()
			except:
				print("Something went screwy. Aborting.")
				self.closedb()
		else:
			print("I couldn't find a database to revert from.")
		
	def run_hybridize(self):
		self.collect_indexes()
		self.hybridize_pair()
		
	def run_evol(self):
		self.collect_indexes()
		self.add_other_evols()
		
class pokedex:
	def __init__(self):
		self.name_to_num = {"Bulbasaur":1,
							"Ivysaur":2,
							"Venusaur":3,
							"Charmander":4,
							"Charmeleon":5,
							"Charizard":6,
							"Squirtle":7,
							"Wartortle":8,
							"Blastoise":9,
							"Caterpie":10,
							"Metapod":11,
							"Butterfree":12,
							"Weedle":13,
							"Kakuna":14,
							"Beedrill":15,
							"Pidgey":16,
							"Pidgeotto":17,
							"Pidgeot":18,
							"Rattata":19,
							"Raticate":20,
							"Spearow":21,
							"Fearow":22,
							"Ekans":23,
							"Arbok":24,
							"Pikachu":25,
							"Raichu":26,
							"Sandshrew":27,
							"Sandslash":28,
							"Nidoran♀":29,
							"Nidorina":30,
							"Nidoqueen":31,
							"Nidoran♂":32,
							"Nidorino":33,
							"Nidoking":34,
							"Clefairy":35,
							"Clefable":36,
							"Vulpix":37,
							"Ninetales":38,
							"Jigglypuff":39,
							"Wigglytuff":40,
							"Zubat":41,
							"Golbat":42,
							"Oddish":43,
							"Gloom":44,
							"Vileplume":45,
							"Paras":46,
							"Parasect":47,
							"Venonat":48,
							"Venomoth":49,
							"Diglett":50,
							"Dugtrio":51,
							"Meowth":52,
							"Persian":53,
							"Psyduck":54,
							"Golduck":55,
							"Mankey":56,
							"Primeape":57,
							"Growlithe":58,
							"Arcanine":59,
							"Poliwag":60,
							"Poliwhirl":61,
							"Poliwrath":62,
							"Abra":63,
							"Kadabra":64,
							"Alakazam":65,
							"Machop":66,
							"Machoke":67,
							"Machamp":68,
							"Bellsprout":69,
							"Weepinbell":70,
							"Victreebel":71,
							"Tentacool":72,
							"Tentacruel":73,
							"Geodude":74,
							"Graveler":75,
							"Golem":76,
							"Ponyta":77,
							"Rapidash":78,
							"Slowpoke":79,
							"Slowbro":80,
							"Magnemite":81,
							"Magneton":82,
							"Farfetch'd":83,
							"Doduo":84,
							"Dodrio":85,
							"Seel":86,
							"Dewgong":87,
							"Grimer":88,
							"Muk":89,
							"Shellder":90,
							"Cloyster":91,
							"Gastly":92,
							"Haunter":93,
							"Gengar":94,
							"Onix":95,
							"Drowzee":96,
							"Hypno":97,
							"Krabby":98,
							"Kingler":99,
							"Voltorb":100,
							"Electrode":101,
							"Exeggcute":102,
							"Exeggutor":103,
							"Cubone":104,
							"Marowak":105,
							"Hitmonlee":106,
							"Hitmonchan":107,
							"Lickitung":108,
							"Koffing":109,
							"Weezing":110,
							"Rhyhorn":111,
							"Rhydon":112,
							"Chansey":113,
							"Tangela":114,
							"Kangaskhan":115,
							"Horsea":116,
							"Seadra":117,
							"Goldeen":118,
							"Seaking":119,
							"Staryu":120,
							"Starmie":121,
							"Mr. Mime":122,
							"Scyther":123,
							"Jynx":124,
							"Electabuzz":125,
							"Magmar":126,
							"Pinsir":127,
							"Tauros":128,
							"Magikarp":129,
							"Gyarados":130,
							"Lapras":131,
							"Ditto":132,
							"Eevee":133,
							"Vaporeon":134,
							"Jolteon":135,
							"Flareon":136,
							"Porygon":137,
							"Omanyte":138,
							"Omastar":139,
							"Kabuto":140,
							"Kabutops":141,
							"Aerodactyl":142,
							"Snorlax":143,
							"Articuno":144,
							"Zapdos":145,
							"Moltres":146,
							"Dratini":147,
							"Dragonair":148,
							"Dragonite":149,
							"Mewtwo":150,
							"Mew":151,
							"Chikorita":152,
							"Bayleef":153,
							"Meganium":154,
							"Cyndaquil":155,
							"Quilava":156,
							"Typhlosion":157,
							"Totodile":158,
							"Croconaw":159,
							"Feraligatr":160,
							"Sentret":161,
							"Furret":162,
							"Hoothoot":163,
							"Noctowl":164,
							"Ledyba":165,
							"Ledian":166,
							"Spinarak":167,
							"Ariados":168,
							"Crobat":169,
							"Chinchou":170,
							"Lanturn":171,
							"Pichu":172,
							"Cleffa":173,
							"Igglybuff":174,
							"Togepi":175,
							"Togetic":176,
							"Natu":177,
							"Xatu":178,
							"Mareep":179,
							"Flaaffy":180,
							"Ampharos":181,
							"Bellossom":182,
							"Marill":183,
							"Azumarill":184,
							"Sudowoodo":185,
							"Politoed":186,
							"Hoppip":187,
							"Skiploom":188,
							"Jumpluff":189,
							"Aipom":190,
							"Sunkern":191,
							"Sunflora":192,
							"Yanma":193,
							"Wooper":194,
							"Quagsire":195,
							"Espeon":196,
							"Umbreon":197,
							"Murkrow":198,
							"Slowking":199,
							"Misdreavus":200,
							"Unown":201,
							"Wobbuffet":202,
							"Girafarig":203,
							"Pineco":204,
							"Forretress":205,
							"Dunsparce":206,
							"Gligar":207,
							"Steelix":208,
							"Snubbull":209,
							"Granbull":210,
							"Qwilfish":211,
							"Scizor":212,
							"Shuckle":213,
							"Heracross":214,
							"Sneasel":215,
							"Teddiursa":216,
							"Ursaring":217,
							"Slugma":218,
							"Magcargo":219,
							"Swinub":220,
							"Piloswine":221,
							"Corsola":222,
							"Remoraid":223,
							"Octillery":224,
							"Delibird":225,
							"Mantine":226,
							"Skarmory":227,
							"Houndour":228,
							"Houndoom":229,
							"Kingdra":230,
							"Phanpy":231,
							"Donphan":232,
							"Porygon2":233,
							"Stantler":234,
							"Smeargle":235,
							"Tyrogue":236,
							"Hitmontop":237,
							"Smoochum":238,
							"Elekid":239,
							"Magby":240,
							"Miltank":241,
							"Blissey":242,
							"Raikou":243,
							"Entei":244,
							"Suicune":245,
							"Larvitar":246,
							"Pupitar":247,
							"Tyranitar":248,
							"Lugia":249,
							"Ho-oh":250,
							"Celebi":251,
							"Azurill":252,
							"Wynaut":253,
							"Ambipom":254,
							"Mismagius":255,
							"Honchkrow":256,
							"Bonsly":257,
							"Mime Jr.":258,
							"Happiny":259,
							"Munchlax":260,
							"Mantyke":261,
							"Weavile":262,
							"Magnezone":263,
							"Lickilicky":264,
							"Rhyperior":265,
							"Tangrowth":266,
							"Electivire":267,
							"Magmortar":268,
							"Togekiss":269,
							"Yanmega":270,
							"Leafeon":271,
							"Glaceon":272,
							"Gliscor":273,
							"Mamoswine":274,
							"Porygon-Z":275,
							"Treecko":276,
							"Grovyle":277,
							"Sceptile":278,
							"Torchic":279,
							"Combusken":280,
							"Blaziken":281,
							"Mudkip":282,
							"Marshtomp":283,
							"Swampert":284,
							"Ralts":285,
							"Kirlia":286,
							"Gardevoir":287,
							"Gallade":288,
							"Shedinja":289,
							"Kecleon":290,
							"Beldum":291,
							"Metang":292,
							"Metagross":293,
							"Bidoof":294,
							"Spiritomb":295,
							"Lucario":296,
							"Gible":297,
							"Gabite":298,
							"Garchomp":299,
							"Mawile":300,
							"Lileep":301,
							"Cradily":302,
							"Anorith":303,
							"Armaldo":304,
							"Cranidos":305,
							"Rampardos":306,
							"Shieldon":307,
							"Bastiodon":308,
							"Slaking":309,
							"Absol":310,
							"Duskull":311,
							"Dusclops":312,
							"Dusknoir":313,
							"Wailord":314,
							"Arceus":315,
							"Turtwig":316,
							"Grotle":317,
							"Torterra":318,
							"Chimchar":319,
							"Monferno":320,
							"Infernape":321,
							"Piplup":322,
							"Prinplup":323,
							"Empoleon":324,
							"Nosepass":325,
							"Probopass":326,
							"Honedge":327,
							"Doublade":328,
							"Aegislash":329,
							"Pawniard":330,
							"Bisharp":331,
							"Luxray":332,
							"Aggron":333,
							"Flygon":334,
							"Milotic":335,
							"Salamence":336,
							"Klinklang":337,
							"Zoroark":338,
							"Sylveon":339,
							"Kyogre":340,
							"Groudon":341,
							"Rayquaza":342,
							"Dialga":343,
							"Palkia":344,
							"Giratina":345,
							"Regigigas":346,
							"Darkrai":347,
							"Genesect":348,
							"Reshiram":349,
							"Zekrom":350,
							"Kyurem":351,
							"Roserade":352,
							"Drifblim":353,
							"Lopunny":354,
							"Breloom":355,
							"Ninjask":356,
							"Banette":357,
							"Rotom":358,
							"Reuniclus":359,
							"Whimsicott":360,
							"Krookodile":361,
							"Cofagrigus":362,
							"Galvantula":363,
							"Ferrothorn":364,
							"Litwick":365,
							"Lampent":366,
							"Chandelure":367,
							"Haxorus":368,
							"Golurk":369,
							"Pyukumuku":370,
							"Klefki":371,
							"Talonflame":372,
							"Mimikyu":373,
							"Volcarona":374,
							"Deino":375,
							"Zweilous":376,
							"Hydreigon":377,
							"Latias":378,
							"Latios":379,
							"Deoxys":380,
							"Jirachi":381,
							"Nincada":382,
							"Bibarel":383,
							"Riolu":384,
							"Slakoth":385,
							"Vigoroth":386,
							"Wailmer":387,
							"Shinx":388,
							"Luxio":389,
							"Aron":390,
							"Lairon":391,
							"Trapinch":392,
							"Vibrava":393,
							"Feebas":394,
							"Bagon":395,
							"Shelgon":396,
							"Klink":397,
							"Klang":398,
							"Zorua":399,
							"Budew":400,
							"Roselia":401,
							"Drifloon":402,
							"Buneary":403,
							"Shroomish":404,
							"Shuppet":405,
							"Solosis":406,
							"Duosion":407,
							"Cottonee":408,
							"Sandile":409,
							"Krokorok":410,
							"Yamask":411,
							"Joltik":412,
							"Ferroseed":413,
							"Axew":414,
							"Fraxure":415,
							"Golett":416,
							"Fletchling":417,
							"Fletchinder":418,
							"Larvesta":419,
							"Stunfisk":420}
							
		self.num_to_name = {1:"Bulbasaur",
							2:"Ivysaur",
							3:"Venusaur",
							4:"Charmander",
							5:"Charmeleon",
							6:"Charizard",
							7:"Squirtle",
							8:"Wartortle",
							9:"Blastoise",
							10:"Caterpie",
							11:"Metapod",
							12:"Butterfree",
							13:"Weedle",
							14:"Kakuna",
							15:"Beedrill",
							16:"Pidgey",
							17:"Pidgeotto",
							18:"Pidgeot",
							19:"Rattata",
							20:"Raticate",
							21:"Spearow",
							22:"Fearow",
							23:"Ekans",
							24:"Arbok",
							25:"Pikachu",
							26:"Raichu",
							27:"Sandshrew",
							28:"Sandslash",
							29:"Nidoran♀",
							30:"Nidorina",
							31:"Nidoqueen",
							32:"Nidoran♂",
							33:"Nidorino",
							34:"Nidoking",
							35:"Clefairy",
							36:"Clefable",
							37:"Vulpix",
							38:"Ninetales",
							39:"Jigglypuff",
							40:"Wigglytuff",
							41:"Zubat",
							42:"Golbat",
							43:"Oddish",
							44:"Gloom",
							45:"Vileplume",
							46:"Paras",
							47:"Parasect",
							48:"Venonat",
							49:"Venomoth",
							50:"Diglett",
							51:"Dugtrio",
							52:"Meowth",
							53:"Persian",
							54:"Psyduck",
							55:"Golduck",
							56:"Mankey",
							57:"Primeape",
							58:"Growlithe",
							59:"Arcanine",
							60:"Poliwag",
							61:"Poliwhirl",
							62:"Poliwrath",
							63:"Abra",
							64:"Kadabra",
							65:"Alakazam",
							66:"Machop",
							67:"Machoke",
							68:"Machamp",
							69:"Bellsprout",
							70:"Weepinbell",
							71:"Victreebel",
							72:"Tentacool",
							73:"Tentacruel",
							74:"Geodude",
							75:"Graveler",
							76:"Golem",
							77:"Ponyta",
							78:"Rapidash",
							79:"Slowpoke",
							80:"Slowbro",
							81:"Magnemite",
							82:"Magneton",
							83:"Farfetch'd",
							84:"Doduo",
							85:"Dodrio",
							86:"Seel",
							87:"Dewgong",
							88:"Grimer",
							89:"Muk",
							90:"Shellder",
							91:"Cloyster",
							92:"Gastly",
							93:"Haunter",
							94:"Gengar",
							95:"Onix",
							96:"Drowzee",
							97:"Hypno",
							98:"Krabby",
							99:"Kingler",
							100:"Voltorb",
							101:"Electrode",
							102:"Exeggcute",
							103:"Exeggutor",
							104:"Cubone",
							105:"Marowak",
							106:"Hitmonlee",
							107:"Hitmonchan",
							108:"Lickitung",
							109:"Koffing",
							110:"Weezing",
							111:"Rhyhorn",
							112:"Rhydon",
							113:"Chansey",
							114:"Tangela",
							115:"Kangaskhan",
							116:"Horsea",
							117:"Seadra",
							118:"Goldeen",
							119:"Seaking",
							120:"Staryu",
							121:"Starmie",
							122:"Mr. Mime",
							123:"Scyther",
							124:"Jynx",
							125:"Electabuzz",
							126:"Magmar",
							127:"Pinsir",
							128:"Tauros",
							129:"Magikarp",
							130:"Gyarados",
							131:"Lapras",
							132:"Ditto",
							133:"Eevee",
							134:"Vaporeon",
							135:"Jolteon",
							136:"Flareon",
							137:"Porygon",
							138:"Omanyte",
							139:"Omastar",
							140:"Kabuto",
							141:"Kabutops",
							142:"Aerodactyl",
							143:"Snorlax",
							144:"Articuno",
							145:"Zapdos",
							146:"Moltres",
							147:"Dratini",
							148:"Dragonair",
							149:"Dragonite",
							150:"Mewtwo",
							151:"Mew",
							152:"Chikorita",
							153:"Bayleef",
							154:"Meganium",
							155:"Cyndaquil",
							156:"Quilava",
							157:"Typhlosion",
							158:"Totodile",
							159:"Croconaw",
							160:"Feraligatr",
							161:"Sentret",
							162:"Furret",
							163:"Hoothoot",
							164:"Noctowl",
							165:"Ledyba",
							166:"Ledian",
							167:"Spinarak",
							168:"Ariados",
							169:"Crobat",
							170:"Chinchou",
							171:"Lanturn",
							172:"Pichu",
							173:"Cleffa",
							174:"Igglybuff",
							175:"Togepi",
							176:"Togetic",
							177:"Natu",
							178:"Xatu",
							179:"Mareep",
							180:"Flaaffy",
							181:"Ampharos",
							182:"Bellossom",
							183:"Marill",
							184:"Azumarill",
							185:"Sudowoodo",
							186:"Politoed",
							187:"Hoppip",
							188:"Skiploom",
							189:"Jumpluff",
							190:"Aipom",
							191:"Sunkern",
							192:"Sunflora",
							193:"Yanma",
							194:"Wooper",
							195:"Quagsire",
							196:"Espeon",
							197:"Umbreon",
							198:"Murkrow",
							199:"Slowking",
							200:"Misdreavus",
							201:"Unown",
							202:"Wobbuffet",
							203:"Girafarig",
							204:"Pineco",
							205:"Forretress",
							206:"Dunsparce",
							207:"Gligar",
							208:"Steelix",
							209:"Snubbull",
							210:"Granbull",
							211:"Qwilfish",
							212:"Scizor",
							213:"Shuckle",
							214:"Heracross",
							215:"Sneasel",
							216:"Teddiursa",
							217:"Ursaring",
							218:"Slugma",
							219:"Magcargo",
							220:"Swinub",
							221:"Piloswine",
							222:"Corsola",
							223:"Remoraid",
							224:"Octillery",
							225:"Delibird",
							226:"Mantine",
							227:"Skarmory",
							228:"Houndour",
							229:"Houndoom",
							230:"Kingdra",
							231:"Phanpy",
							232:"Donphan",
							233:"Porygon2",
							234:"Stantler",
							235:"Smeargle",
							236:"Tyrogue",
							237:"Hitmontop",
							238:"Smoochum",
							239:"Elekid",
							240:"Magby",
							241:"Miltank",
							242:"Blissey",
							243:"Raikou",
							244:"Entei",
							245:"Suicune",
							246:"Larvitar",
							247:"Pupitar",
							248:"Tyranitar",
							249:"Lugia",
							250:"Ho-oh",
							251:"Celebi",
							252:"Azurill",
							253:"Wynaut",
							254:"Ambipom",
							255:"Mismagius",
							256:"Honchkrow",
							257:"Bonsly",
							258:"Mime Jr.",
							259:"Happiny",
							260:"Munchlax",
							261:"Mantyke",
							262:"Weavile",
							263:"Magnezone",
							264:"Lickilicky",
							265:"Rhyperior",
							266:"Tangrowth",
							267:"Electivire",
							268:"Magmortar",
							269:"Togekiss",
							270:"Yanmega",
							271:"Leafeon",
							272:"Glaceon",
							273:"Gliscor",
							274:"Mamoswine",
							275:"Porygon-Z",
							276:"Treecko",
							277:"Grovyle",
							278:"Sceptile",
							279:"Torchic",
							280:"Combusken",
							281:"Blaziken",
							282:"Mudkip",
							283:"Marshtomp",
							284:"Swampert",
							285:"Ralts",
							286:"Kirlia",
							287:"Gardevoir",
							288:"Gallade",
							289:"Shedinja",
							290:"Kecleon",
							291:"Beldum",
							292:"Metang",
							293:"Metagross",
							294:"Bidoof",
							295:"Spiritomb",
							296:"Lucario",
							297:"Gible",
							298:"Gabite",
							299:"Garchomp",
							300:"Mawile",
							301:"Lileep",
							302:"Cradily",
							303:"Anorith",
							304:"Armaldo",
							305:"Cranidos",
							306:"Rampardos",
							307:"Shieldon",
							308:"Bastiodon",
							309:"Slaking",
							310:"Absol",
							311:"Duskull",
							312:"Dusclops",
							313:"Dusknoir",
							314:"Wailord",
							315:"Arceus",
							316:"Turtwig",
							317:"Grotle",
							318:"Torterra",
							319:"Chimchar",
							320:"Monferno",
							321:"Infernape",
							322:"Piplup",
							323:"Prinplup",
							324:"Empoleon",
							325:"Nosepass",
							326:"Probopass",
							327:"Honedge",
							328:"Doublade",
							329:"Aegislash",
							330:"Pawniard",
							331:"Bisharp",
							332:"Luxray",
							333:"Aggron",
							334:"Flygon",
							335:"Milotic",
							336:"Salamence",
							337:"Klinklang",
							338:"Zoroark",
							339:"Sylveon",
							340:"Kyogre",
							341:"Groudon",
							342:"Rayquaza",
							343:"Dialga",
							344:"Palkia",
							345:"Giratina",
							346:"Regigigas",
							347:"Darkrai",
							348:"Genesect",
							349:"Reshiram",
							350:"Zekrom",
							351:"Kyurem",
							352:"Roserade",
							353:"Drifblim",
							354:"Lopunny",
							355:"Breloom",
							356:"Ninjask",
							357:"Banette",
							358:"Rotom",
							359:"Reuniclus",
							360:"Whimsicott",
							361:"Krookodile",
							362:"Cofagrigus",
							363:"Galvantula",
							364:"Ferrothorn",
							365:"Litwick",
							366:"Lampent",
							367:"Chandelure",
							368:"Haxorus",
							369:"Golurk",
							370:"Pyukumuku",
							371:"Klefki",
							372:"Talonflame",
							373:"Mimikyu",
							374:"Volcarona",
							375:"Deino",
							376:"Zweilous",
							377:"Hydreigon",
							378:"Latias",
							379:"Latios",
							380:"Deoxys",
							381:"Jirachi",
							382:"Nincada",
							383:"Bibarel",
							384:"Riolu",
							385:"Slakoth",
							386:"Vigoroth",
							387:"Wailmer",
							388:"Shinx",
							389:"Luxio",
							390:"Aron",
							391:"Lairon",
							392:"Trapinch",
							393:"Vibrava",
							394:"Feebas",
							395:"Bagon",
							396:"Shelgon",
							397:"Klink",
							398:"Klang",
							399:"Zorua",
							400:"Budew",
							401:"Roselia",
							402:"Drifloon",
							403:"Buneary",
							404:"Shroomish",
							405:"Shuppet",
							406:"Solosis",
							407:"Duosion",
							408:"Cottonee",
							409:"Sandile",
							410:"Krokorok",
							411:"Yamask",
							412:"Joltik",
							413:"Ferroseed",
							414:"Axew",
							415:"Fraxure",
							416:"Golett",
							417:"Fletchling",
							418:"Fletchinder",
							419:"Larvesta",
							420:"Stunfisk"}
							
		self.relationships = {"Bulbasaur":["Ivysaur", "Venusaur"],
							"Ivysaur":["Bulbasaur", "Venusaur"],
							"Venusaur":["Bulbasaur", "Ivysaur"],
							"Charmander":["Charmeleon", "Charizard"],
							"Charmeleon":["Charmander", "Charizard"],
							"Charizard":["Charmander", "Charmeleon"],
							"Squirtle":["Wartortle", "Blastoise"],
							"Wartortle":["Squirtle", "Blastoise"],
							"Blastoise":["Squirtle", "Wartortle"],
							"Caterpie":["Metapod", "Butterfree"],
							"Metapod":["Caterpie", "Butterfree"],
							"Butterfree":["Caterpie", "Metapod"],
							"Weedle":["Kakuna", "Beedrill"],
							"Kakuna":["Weedle", "Beedrill"],
							"Beedrill":["Weedle", "Kakuna"],
							"Pidgey":["Pidgeotto", "Pidgeot"],
							"Pidgeotto":["Pidgey", "Pidgeot"],
							"Pidgeot":["Pidgey", "Pidgeotto"],
							"Rattata":["Raticate"],
							"Raticate":["Rattata"],
							"Spearow":["Fearow"],
							"Fearow":["Spearow"],
							"Ekans":["Arbok"],
							"Arbok":["Ekans"],
							"Pikachu":["Pichu", "Raichu"],
							"Raichu":["Pichu", "Pikachu"],
							"Sandshrew":["Sandslash"],
							"Sandslash":["Sandshrew"],
							"Nidoran♀":["Nidorina", "Nidoqueen"],
							"Nidorina":["Nidoran♀", "Nidoqueen"],
							"Nidoqueen":["Nidoran♀", "Nidorina"],
							"Nidoran♂":["Nidorino", "Nidoking"],
							"Nidorino":["Nidoran♂", "Nidoking"],
							"Nidoking":["Nidoran♂", "Nidorino"],
							"Clefairy":["Cleffa", "Clefable"],
							"Clefable":["Cleffa", "Clefairy"],
							"Vulpix":["Ninetales"],
							"Ninetales":["Vulpix"],
							"Jigglypuff":["Igglybuff", "Wigglytuff"],
							"Wigglytuff":["Igglybuff", "Jigglypuff"],
							"Zubat":["Golbat", "Crobat"],
							"Golbat":["Zubat", "Crobat"],
							"Oddish":["Gloom", "Vileplume", "Bellossom"],
							"Gloom":["Oddish", "Vileplume", "Bellossom"],
							"Vileplume":["Oddish", "Gloom"],
							"Paras":["Parasect"],
							"Parasect":["Paras"],
							"Venonat":["Venomoth"],
							"Venomoth":["Venonat"],
							"Diglett":["Dugtrio"],
							"Dugtrio":["Diglett"],
							"Meowth":["Persian"],
							"Persian":["Meowth"],
							"Psyduck":["Golduck"],
							"Golduck":["Psyduck"],
							"Mankey":["Primeape"],
							"Primeape":["Mankey"],
							"Growlithe":["Arcanine"],
							"Arcanine":["Growlithe"],
							"Poliwag":["Poliwhirl", "Poliwrath", "Politoed"],
							"Poliwhirl":["Poliwag", "Poliwrath", "Politoed"],
							"Poliwrath":["Poliwag", "Poliwhirl"],
							"Abra":["Kadabra", "Alakazam"],
							"Kadabra":["Abra", "Alakazam"],
							"Alakazam":["Abra", "Kadabra"],
							"Machop":["Machoke", "Machamp"],
							"Machoke":["Machop", "Machamp"],
							"Machamp":["Machop", "Machoke"],
							"Bellsprout":["Weepinbell", "Victreebel"],
							"Weepinbell":["Bellsprout", "Victreebel"],
							"Victreebel":["Bellsprout", "Weepinbell"],
							"Tentacool":["Tentacruel"],
							"Tentacruel":["Tentacool"],
							"Geodude":["Graveler", "Golem"],
							"Graveler":["Geodude", "Golem"],
							"Golem":["Geodude", "Graveler"],
							"Ponyta":["Rapidash"],
							"Rapidash":["Ponyta"],
							"Slowpoke":["Slowbro", "Slowking"],
							"Slowbro":["Slowpoke", "Slowking"],
							"Magnemite":["Magneton", "Magnezone"],
							"Magneton":["Magnemite", "Magnezone"],
							"Farfetch'd":[],
							"Doduo":["Dodrio"],
							"Dodrio":["Doduo"],
							"Seel":["Dewgong"],
							"Dewgong":["Seel"],
							"Grimer":["Muk"],
							"Muk":["Grimer"],
							"Shellder":["Cloyster"],
							"Cloyster":["Shellder"],
							"Gastly":["Haunter", "Gengar"],
							"Haunter":["Gastly", "Gengar"],
							"Gengar":["Gastly", "Haunter"],
							"Onix":["Steelix"],
							"Drowzee":["Hypno"],
							"Hypno":["Drowzee"],
							"Krabby":["Kingler"],
							"Kingler":["Krabby"],
							"Voltorb":["Electrode"],
							"Electrode":["Voltorb"],
							"Exeggcute":["Exeggutor"],
							"Exeggutor":["Exeggcute"],
							"Cubone":["Marowak"],
							"Marowak":["Cubone"],
							"Hitmonlee":["Tyrogue"],
							"Hitmonchan":["Tyrogue"],
							"Lickitung":["Lickilicky"],
							"Koffing":["Weezing"],
							"Weezing":["Koffing"],
							"Rhyhorn":["Rhydon", "Rhyperior"],
							"Rhydon":["Rhyhorn", "Rhyperior"],
							"Chansey":["Happiny", "Blissey"],
							"Tangela":["Tangrowth"],
							"Kangaskhan":[],
							"Horsea":["Seadra", "Kingdra"],
							"Seadra":["Horsea", "Kingdra"],
							"Goldeen":["Seaking"],
							"Seaking":["Goldeen"],
							"Staryu":["Starmie"],
							"Starmie":["Staryu"],
							"Mr. Mime":["Mime Jr."],
							"Scyther":["Scizor"],
							"Jynx":["Smoochum"],
							"Electabuzz":["Elekid", "Electivire"],
							"Magmar":["Magby", "Magmortar"],
							"Pinsir":[],
							"Tauros":[],
							"Magikarp":["Gyarados"],
							"Gyarados":["Magikarp"],
							"Lapras":[],
							"Ditto":[],
							"Eevee":["Vaporeon", "Jolteon", "Flareon", "Espeon", "Umbreon", "Leafeon", "Glaceon", "Sylveon"],
							"Vaporeon":["Eevee"],
							"Jolteon":["Eevee"],
							"Flareon":["Eevee"],
							"Porygon":["Porygon2", "Porygon-Z"],
							"Omanyte":["Omastar"],
							"Omastar":["Omanyte"],
							"Kabuto":["Kabutops"],
							"Kabutops":["Kabuto"],
							"Aerodactyl":[],
							"Snorlax":["Munchlax"],
							"Articuno":[],
							"Zapdos":[],
							"Moltres":[],
							"Dratini":["Dragonair", "Dragonite"],
							"Dragonair":["Dratini", "Dragonite"],
							"Dragonite":["Dratini", "Dragonair"],
							"Mewtwo":[],
							"Mew":[],
							"Chikorita":["Bayleef", "Meganium"],
							"Bayleef":["Chikorita", "Meganium"],
							"Meganium":["Chikorita", "Bayleef"],
							"Cyndaquil":["Quilava", "Typhlosion"],
							"Quilava":["Cyndaquil", "Typhlosion"],
							"Typhlosion":["Cyndaquil", "Quilava"],
							"Totodile":["Croconaw", "Feraligatr"],
							"Croconaw":["Totodile", "Feraligatr"],
							"Feraligatr":["Totodile", "Croconaw"],
							"Sentret":["Furret"],
							"Furret":["Sentret"],
							"Hoothoot":["Noctowl"],
							"Noctowl":["Hoothoot"],
							"Ledyba":["Ledian"],
							"Ledian":["Ledyba"],
							"Spinarak":["Ariados"],
							"Ariados":["Spinarak"],
							"Crobat":["Zubat", "Golbat"],
							"Chinchou":["Lanturn"],
							"Lanturn":["Chinchou"],
							"Pichu":["Pikachu", "Raichu"],
							"Cleffa":["Clefairy", "Clefable"],
							"Igglybuff":["Jigglypuff", "Wigglytuff"],
							"Togepi":["Togetic", "Togekiss"],
							"Togetic":["Togepi", "Togekiss"],
							"Natu":["Xatu"],
							"Xatu":["Natu"],
							"Mareep":["Flaaffy", "Ampharos"],
							"Flaaffy":["Mareep", "Ampharos"],
							"Ampharos":["Mareep", "Flaaffy"],
							"Bellossom":["Oddish", "Gloom"],
							"Marill":["Azurill", "Azumarill"],
							"Azumarill":["Azurill", "Marill"],
							"Sudowoodo":["Bonsly"],
							"Politoed":["Poliwag", "Poliwhirl"],
							"Hoppip":["Skiploom", "Jumpluff"],
							"Skiploom":["Hoppip", "Jumpluff"],
							"Jumpluff":["Hoppip", "Skiploom"],
							"Aipom":["Ambipom"],
							"Sunkern":["Sunflora"],
							"Sunflora":["Sunkern"],
							"Yanma":["Yanmega"],
							"Wooper":["Quagsire"],
							"Quagsire":["Wooper"],
							"Espeon":["Eevee"],
							"Umbreon":["Eevee"],
							"Murkrow":["Honchkrow"],
							"Slowking":["Slowpoke", "Slowbro"],
							"Misdreavus":["Mismagius"],
							"Unown":[],
							"Wobbuffet":["Wynaut"],
							"Girafarig":[],
							"Pineco":["Forretress"],
							"Forretress":["Pineco"],
							"Dunsparce":[],
							"Gligar":["Gliscor"],
							"Steelix":["Onix"],
							"Snubbull":["Granbull"],
							"Granbull":["Snubbull"],
							"Qwilfish":[],
							"Scizor":["Scyther"],
							"Shuckle":[],
							"Heracross":[],
							"Sneasel":["Weavile"],
							"Teddiursa":["Ursaring"],
							"Ursaring":["Teddiursa"],
							"Slugma":["Magcargo"],
							"Magcargo":["Slugma"],
							"Swinub":["Piloswine", "Mamoswine"],
							"Piloswine":["Swinub", "Mamoswine"],
							"Corsola":[],
							"Remoraid":["Octillery"],
							"Octillery":["Remoraid"],
							"Delibird":[],
							"Mantine":["Mantyke"],
							"Skarmory":[],
							"Houndour":["Houndoom"],
							"Houndoom":["Houndour"],
							"Kingdra":["Horsea", "Seadra"],
							"Phanpy":["Donphan"],
							"Donphan":["Phanpy"],
							"Porygon2":["Porygon", "Porygon-Z"],
							"Stantler":[],
							"Smeargle":[],
							"Tyrogue":["Hitmonlee", "Hitmonchan", "Hitmontop"],
							"Hitmontop":["Tyrogue"],
							"Smoochum":["Jynx"],
							"Elekid":["Electabuzz", "Electivire"],
							"Magby":["Magmar", "Magmortar"],
							"Miltank":[],
							"Blissey":["Happiny", "Chansey"],
							"Raikou":[],
							"Entei":[],
							"Suicune":[],
							"Larvitar":["Pupitar", "Tyranitar"],
							"Pupitar":["Larvitar", "Tyranitar"],
							"Tyranitar":["Larvitar", "Pupitar"],
							"Lugia":[],
							"Ho-oh":[],
							"Celebi":[],
							"Azurill":["Marill", "Azumarill"],
							"Wynaut":["Wobbuffet"],
							"Ambipom":["Aipom"],
							"Mismagius":["Misdreavus"],
							"Honchkrow":["Murkrow"],
							"Bonsly":["Sudowoodo"],
							"Mime Jr.":["Mr. Mime"],
							"Happiny":["Chansey", "Blissey"],
							"Munchlax":["Snorlax"],
							"Mantyke":["Mantine"],
							"Weavile":["Sneasel"],
							"Magnezone":["Magnemite", "Magneton"],
							"Lickilicky":["Lickitung"],
							"Rhyperior":["Rhyhorn", "Rhydon"],
							"Tangrowth":["Tangela"],
							"Electivire":["Elekid", "Electabuzz"],
							"Magmortar":["Magby", "Magmar"],
							"Togekiss":["Togepi", "Togetic"],
							"Yanmega":["Yanma"],
							"Leafeon":["Eevee"],
							"Glaceon":["Eevee"],
							"Gliscor":["Gligar"],
							"Mamoswine":["Swinub", "Piloswine"],
							"Porygon-Z":["Porygon", "Porygon2"],
							"Treecko":["Grovyle", "Sceptile"],
							"Grovyle":["Treecko", "Sceptile"],
							"Sceptile":["Treecko", "Sceptile"],
							"Torchic":["Combusken", "Blaziken"],
							"Combusken":["Torchic", "Blaziken"],
							"Blaziken":["Torchic", "Combusken"],
							"Mudkip":["Marshtomp", "Swampert"],
							"Marshtomp":["Mudkip", "Swampert"],
							"Swampert":["Mudkip", "Marshtomp"],
							"Ralts":["Kirlia", "Gardevoir", "Gallade"],
							"Kirlia":["Ralts", "Gardevoir", "Gallade"],
							"Gardevoir":["Ralts", "Kirlia"],
							"Gallade":["Ralts", "Kirlia"],
							"Shedinja":["Nincada"],
							"Kecleon":[],
							"Beldum":["Metang", "Metagross"],
							"Metang":["Beldum", "Metagross"],
							"Metagross":["Beldum", "Metang"],
							"Bidoof":["Bibarel"],
							"Spiritomb":[],
							"Lucario":["Riolu"],
							"Gible":["Gabite", "Garchomp"],
							"Gabite":["Gible", "Garchomp"],
							"Garchomp":["Gible", "Gabite"],
							"Mawile":[],
							"Lileep":["Cradily"],
							"Cradily":["Lileep"],
							"Anorith":["Armaldo"],
							"Armaldo":["Anorith"],
							"Cranidos":["Rampardos"],
							"Rampardos":["Cranidos"],
							"Shieldon":["Bastiodon"],
							"Bastiodon":["Shieldon"],
							"Slaking":["Slakoth", "Vigoroth"],
							"Absol":[],
							"Duskull":["Dusclops", "Dusknoir"],
							"Dusclops":["Duskull", "Dusknoir"],
							"Dusknoir":["Duskull", "Dusclops"],
							"Wailord":["Wailmer"],
							"Arceus":[],
							"Turtwig":["Grotle", "Torterra"],
							"Grotle":["Turtwig", "Torterra"],
							"Torterra":["Turtwig", "Grotle"],
							"Chimchar":["Monferno", "Infernape"],
							"Monferno":["Chimchar", "Infernape"],
							"Infernape":["Chimchar", "Monferno"],
							"Piplup":["Prinplup", "Empoleon"],
							"Prinplup":["Piplup", "Empoleon"],
							"Empoleon":["Piplup", "Prinplup"],
							"Nosepass":["Probopass"],
							"Probopass":["Nosepass"],
							"Honedge":["Doublade", "Aegislash"],
							"Doublade":["Honedge", "Aegislash"],
							"Aegislash":["Honedge", "Doublade"],
							"Pawniard":["Bisharp"],
							"Bisharp":["Pawniard"],
							"Luxray":["Shinx", "Luxio"],
							"Aggron":["Aron", "Lairon"],
							"Flygon":["Trapinch", "Vibrava"],
							"Milotic":["Feebas"],
							"Salamence":["Bagon", "Shelgon"],
							"Klinklang":["Klink", "Klang"],
							"Zoroark":["Zorua"],
							"Sylveon":["Eevee"],
							"Kyogre":[],
							"Groudon":[],
							"Rayquaza":[],
							"Dialga":[],
							"Palkia":[],
							"Giratina":[],
							"Regigigas":[],
							"Darkrai":[],
							"Genesect":[],
							"Reshiram":[],
							"Zekrom":[],
							"Kyurem":[],
							"Roserade":["Budew", "Roselia"],
							"Drifblim":["Drifloon"],
							"Lopunny":["Buneary"],
							"Breloom":["Shroomish"],
							"Ninjask":["Nincada"],
							"Banette":["Shuppet"],
							"Rotom":[],
							"Reuniclus":["Solosis", "Duosion"],
							"Whimsicott":["Cottonee"],
							"Krookodile":["Sandile", "Krokorok"],
							"Cofagrigus":["Yamask"],
							"Galvantula":["Joltik"],
							"Ferrothorn":["Ferroseed"],
							"Litwick":["Lampent", "Chandelure"],
							"Lampent":["Litwick", "Chandelure"],
							"Chandelure":["Litwick", "Lampent"],
							"Haxorus":["Axew", "Fraxure"],
							"Golurk":["Golett"],
							"Pyukumuku":[],
							"Klefki":[],
							"Talonflame":["Fletchling", "Fletchinder"],
							"Mimikyu":[],
							"Volcarona":["Larvesta"],
							"Deino":["Zweilous", "Hydreigon"],
							"Zweilous":["Deino", "Hydreigon"],
							"Hydreigon":["Deino", "Zweilous"],
							"Latias":[],
							"Latios":[],
							"Deoxys":[],
							"Jirachi":[],
							"Nincada":["Ninjask", "Shedinja"],
							"Bibarel":["Bidoof"],
							"Riolu":["Lucario"],
							"Slakoth":["Vigoroth", "Slaking"],
							"Vigoroth":["Slakoth", "Slaking"],
							"Wailmer":["Wailord"],
							"Shinx":["Luxio", "Luxray"],
							"Luxio":["Shinx", "Luxray"],
							"Aron":["Lairon", "Aggron"],
							"Lairon":["Aron", "Aggron"],
							"Trapinch":["Vibrava", "Flygon"],
							"Vibrava":["Trapinch", "Flygon"],
							"Feebas":["Milotic"],
							"Bagon":["Shelgon", "Salamence"],
							"Shelgon":["Bagon", "Salamence"],
							"Klink":["Klang", "Klinklang"],
							"Klang":["Klink", "Klinklang"],
							"Zorua":["Zoroark"],
							"Budew":["Roselia", "Roserade"],
							"Roselia":["Budew", "Roserade"],
							"Drifloon":["Drifblim"],
							"Buneary":["Lopunny"],
							"Shroomish":["Breloom"],
							"Shuppet":["Banette"],
							"Solosis":["Duosion", "Reuniclus"],
							"Duosion":["Solosis", "Reuniclus"],
							"Cottonee":["Whimsicott"],
							"Sandile":["Krokorok", "Krookodile"],
							"Krokorok":["Sandile", "Krookodile"],
							"Yamask":["Cofagrigus"],
							"Joltik":["Galvantula"],
							"Ferroseed":["Ferrothorn"],
							"Axew":["Fraxure", "Haxorus"],
							"Fraxure":["Axew", "Haxorus"],
							"Golett":["Golurk"],
							"Fletchling":["Fletchinder", "Talonflame"],
							"Fletchinder":["Fletchling", "Talonflame"],
							"Larvesta":["Volcarona"],
							"Stunfisk":[]}
							
def options():
	parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
			description='''Infinite fusion hybridizer
			
			Put this script in your infinite fusion install directory and run with python 3+
			
			Pokemon names MUST start with capital letters.
			
			Choose one of three actions:
				hybrid [Pokemon 1] [Pokemon 2] - Add head-body fusions for a pair of pokemon to the body-head combo as additional alts and vice versa
				evol [Pokemon 1] [Pokemon 2] - Add all fusions of any evolutions of Pokemon 1 + pokemon 2 to pokemon1+pokemon 2
												ex: Banette + Sandslash has 
				revert [Pokemon 1] - Delete any files that THIS SCRIPT has added to Pokemon 1's custom sprites
				
			''')
			
	
	
	parser.add_argument('-p1',  dest = 'pok_1', default = None, help =  '')
	parser.add_argument('-p2',  dest = 'pok_2', default = None, help =  '')
	
	args, unknown = parser.parse_known_args()
	
	return parser, args
		
def main():
	p, a = options()
	
	if len(sys.argv) < 2:
		p.print_help()
		sys.exit()
	
	p1 = a.pok_1
	p2 = a.pok_2
		
	ok_actions = ["hybrid", "evol", "revert"]
	action = sys.argv[1]
	
	if action not in ok_actions:
		print("First argument has to be in:", ok_actions)
		print("Try again")
		p.print_help()
		sys.exit()
		
	if action == "hybrid" or action == "evol":
		if p1 is None or p2 is None:
			print("You need to give two pokemon for this tool to work")
			p.print_help()
			sys.exit()
		
	if action == "hybrid":
		mn = sprite_hybridizer(p1, p2)
		mn.run_hybridize()
		
	if action == "evol":
		mn = sprite_hybridizer(p1, p2)
		mn.run_evol()
	
	if action == "revert":
		if p1 is None:
			print("You have to give a pokemon to revert changes")
			p.print_help()
			sys.exit()
		else:
			mn = sprite_hybridizer()
			mn.restore_from_log(p1)
	
main()
