# Infinite-fusion-hybridizer
A python script for merging head-body and body-head pokemon infinite fusion sprites

With this script, you can add the fusions for a head-body pair to the opposite and vice versa. If you like the stats, typing, or abilities of a head+body fusion like Charizard+Venusar but prefer the way that Venusaur+Charizard looks, you can make that happen with:

hybridize_sprites hybrid -p1 Charizard -p2 Venusar

You can also add all of the fusions of two pokemon's evolutionary lines, e.g. 

hybridize_sprites evol -p1 Banette -p2 Sandslash

Adds banette + sandshrew, banette + sandslash, shuppet + sandshrew, and shuppet + sandslah to banette + sandslash's alternative sprites.

You can also remove changes to a pokemon with

hybridize_sprites evol -p1 [Pokemon]
