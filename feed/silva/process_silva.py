''''
Script received from Jessica Grant, 8 October 2013

This script takes as input the ssu fasta from Silva (in this case SSURef_NR99_115_tax_silva.fasta
but change as necessary.)  Also 'tax_rank.txt' for the rank file from Silva ftp.

It outputs 
	the taxonomy in this format:
	<taxid>\t|\t<parentid>\t|\t<taxon>\t|\t<rank>\t|\t<seqid>
	also two additional files that might not be necessary:
	homonym_paths.txt for checking taxa called as homonyms
	silva_taxonly.txt a list of the taxa that are included in the taxonomy.

seqid is the unique identifier from Silva of the SSU sequence, and is there for the species only.  Other 
ranks have 'no seq'

Be aware of a few things - 
	I have ignored plants, animals and fungi because they have reasonable taxonomies elsewhere.

	Silva has 'uncultured' as a taxon, between the species and its genus. e.g.:
	
>U81762.1.1448 Bacteria;Firmicutes;Clostridia;Clostridiales;Ruminococcaceae;uncultured;uncultured bacterium
	
	I have ignored this so this uncultured bacterium would get mapped to Ruminococcaceae

	All duplicate species names get their own unique number, but duplicate names of genera or above
	are checked for homonyms. - Homonyms are determined by having different parents - in some cases this
	can add taxa that really are the same.  e.g. Dinobryon here:
	
['Eukaryota', 'SAR', 'Stramenopiles', 'Chrysophyceae', 'Ochromonadales', 'Dinobryon', 'Dinobryon divergens']
['Eukaryota', 'SAR', 'Stramenopiles', 'Chrysophyceae', 'Ochromonadales', 'Ochromonas', 'Dinobryon', 'Dinobryon cf. sociale']	

	
	Other problems exist in Silva - for example in these two paths, 'marine group' is treated as a taxon (and is 
	picked up as homonymic) when it really isn't.
	
['Bacteria', 'Acidobacteria', 'Holophagae', 'Holophagales', 'Holophagaceae', 'marine group', 'uncultured bacterium']
['Bacteria', 'Cyanobacteria', 'SubsectionI', 'FamilyI', 'marine group', 'cyanobacterium UCYN-A']

	Or  here, where '43F-1404R' seems to be treated as a taxon when it is probably a primer set: 
	
['Bacteria', 'Acidobacteria', 'Holophagae', 'Subgroup 10', '43F-1404R', 'uncultured Acidobacteria bacterium']
['Bacteria', 'Proteobacteria', 'Deltaproteobacteria', '43F-1404R', 'uncultured bacterium']

	
	I left in things like 'Bacteria', 'Cyanobacteria', 'Chloroplast', 'Oryza sativa Japonica Group'
	even though the it could be confusing.  Chloroplast (and other symbiont) data may need special treatment

'''
import sys
import re
import string
import os, time, json, os.path


def writeAboutFile(url, nodesfilename, taxdir):
	aboutfilename = taxdir+"/about.json"
	aboutfile = open(aboutfilename,"w")
	# Get file date from nodes.dmp in downloaddir
	# os.path.getmtime(file)   => number of seconds since epoch
	filetime = os.path.getmtime(nodesfilename)
	tuple_time = time.gmtime(filetime)
	iso_time = time.strftime("%Y-%m-%dT%H:%M:%S", tuple_time)
	# This is pretty much garbage, pending overhaul of the metadata feature.
	about = {"type": "source",
			 "namespace": {"prefix": "silva",
					   	   "definition": "http://www.arb-silva.de/browser/ssu/silva/",
					  	   "description": "SILVA Taxonomy"},
			 "prefix": "silva",
			 "namespaces": [],
			 "url": url,
			 "lastModified": iso_time,
			 "smush": False}
	aboutfile.write(json.dumps(about))
	print "Wrote", aboutfilename
	aboutfile.close()

pathdict = {} #given the sequence identifier, return the taxonomy path
seqdict = {} #given the taxon name, return (<species id assigned here>,<unique sequence id from SSU ref file>) 
Seen = {} # to tell whether the taxon name has been seen before - to know if homonym check needs to be done
taxondict = {}  # maps (parentid, name) to taxid

# It was judged that other taxonomies on balance will be better than Silva
# for certain groups.
# Silva classifies ABEG02010941 Caenorhabditis brenneri as a bacterium; this 
# is clearly an artifact of sample contamination.

kill = re.compile('|'.join(['ABEG02010941',  # Caenorhabditis brenneri
							'ABRM01041397',  # Hydra magnipapillata
							'ALWT01111512',  # Myotis davidii
							'HP641760',		 # Alasmidonta varicosa
							'JR876587',  	 # Embioptera sp. UVienna-2012
							 ]))

# AB564305 AB564301 AB564299 ... all garbage

def makePathDict(infilename, outfilename):
	infile = open(infilename,'rU')
	outfile = open(outfilename,'w') # I'm writing this out to have the taxonomy separate from the sequences - not necessary
	inclusive = 0
	exclusive = 0
	for line in infile:  #removing plants, animals, fungi, chloroplast and mitochondrial sequences - also specifying Oryza because it is problematic in this version the database (SSURef_NR99_115_tax_silva.fasta).
		if line[0] == '>':
			inclusive += 1
			if not re.search(kill,line):
				exclusive += 1
				taxlist = []		
				uid = line.split()[0].strip() # was going to use the species but there are multiple 'unidentified', for example
				taxlist_1  = line.strip(uid).strip().split(';')
				uid = uid.lstrip('>')
				for taxname in taxlist_1:
					# JAR commented out the following... smasher takes care of these
					# if not re.search('Incertae Sedis',tax) and tax not in taxlist:			
					taxlist.append(taxname)
				#if 'uncultured' in taxlist:
				#	taxlist.remove('uncultured') #not sure...
				pathdict[uid] = taxlist
				outfile.write(uid + ',' + str(pathdict[uid]) + '\n')
	outfile.close()		
	print "Silva tips: %s  Exclusive of kill list: %s"%(inclusive, exclusive)
	return pathdict	

def checkHomonym(uid,taxon,pathdict,olduid,homfilename):
	newpath = pathdict[uid]
	oldpath = pathdict[olduid]
	newparindex = pathdict[uid].index(taxon) - 1
	oldparindex = pathdict[olduid].index(taxon) - 1
	if oldpath[oldparindex] in newpath[newparindex] and oldpath[oldparindex]: #parent of original in new path
		return True #link new to old
	else:
		hom_outfile = open(homfilename,'a')
		hom_outfile.write(taxon + ',' + str(newpath)+ ',' +str(oldpath) + '\n')
		hom_outfile.close()
		return newpath[newparindex]

ranks = {}

def readRanks(indir):
	rankfilename = indir + '/tax_ranks.txt'
	rankfile = open(rankfilename,'r')
	for line in rankfile:
		path,node,rank,remark = line.split('\t')
		components = path.split(';')
		if len(components) >= 2:
			rank_key = (node,components[-2])
			if rank_key in ranks and ranks[rank_key] != rank:
				print "Homonym with parent homonym", rank_key
				ranks[rank_key] = 'no rank'
			else:
				ranks[rank_key] = rank
	rankfile.close()

accession_to_ncbi = {}

def readNcbi(indir):
	ncbifilename = indir + "/accessionid_to_taxonid.tsv"
	ncbifile = open(ncbifilename, 'r')
	for line in ncbifile:
		fields = line.split('\t')
		if len(fields) >= 2 and fields[1] != '':
			accession_to_ncbi[fields[0]] = fields[1].strip()
	ncbifile.close()

synonyms = {}
ncbi_silva_parent = {}
ncbi_sample_accession = {}
ncbi_name = {}
ncbi_to_accession_unique = {}

def processSilva(pathdict, indir, outdir):
	rank = 'no rank' #for now
	outfile = open(outdir + '/taxonomy.tsv','w')
	outfile.write('uid\t|\tparent_uid\t|\tname\t|\trank\t|\tsourceinfo\t|\t\n')
	outfile.write('0\t|\t\t|\tlife\t|\tno rank\t|\t\t|\t\n')
	homfilename = outdir + '/homonym_paths.txt'
	missing = []
	blocked = 0
	internal = 0
	tips = 0
	acc_success = 0
	acc_seen = {}

	uids = [uid for (z, uid) in sorted([(len(uid), uid) for uid in pathdict.keys()])]

    # uid is a unique sequence id e.g. A58083.1.1474
	for uid in uids:
		parentid = "0"
		path = pathdict[uid]
		accession = string.split(uid,".",1)[0]
		for depth in range(0, len(path)-1):
			taxname = path[depth]
			taxon_key = (parentid, taxname)
			if taxon_key in taxondict:
				taxid = taxondict[taxon_key]    #smasher id
			else:
				taxid = "%s/#%d"%(accession, depth+1)
				# Use this URL prefix: http://www.arb-silva.de/browser/ssu/silva/
				internal = internal + 1
				if depth == 0:  #taxname in ['Bacteria','Eukaryota','Archaea']: 
					rank = 'domain'
				else:									
					#returns true if this taxon and the one in the db have the same parent
					if taxname in seqdict:
						checkHomonym(uid,taxname,pathdict,seqdict[taxname],homfilename)
					rank = 'no rank'
					# We considered using tax_ranks but they're not helpful.

				seqdict[taxname] = uid
				taxondict[taxon_key] = taxid

				# Some of the 'uncultured' taxa are incorrectly assigned rank 'class' or 'order'
				if taxname == 'uncultured':
					rank = 'no rank'
				outfile.write("%s\t|\t%s\t|\t%s\t|\t%s\t|\t\t|\t\n" %
							  (taxid, parentid, taxname, rank))

			parentid = taxid    #for next iteration

			# Don't descend into groups that need to be suppressed
			if taxname in ['Metazoa',
						   'Fungi',
						   'Chloroplast',
						   'mitochondria',
						   'Herdmania',
						   'Oryza',
						   'Chloroplastida',
						   ]:
				parentid = None
				if taxname == 'Chloroplastida':
					# What NCBI calls it
					synonyms['Viridiplantae'] = taxid
					# What GBIF calls it
					synonyms['Plantae'] = taxid
				elif taxname == 'Metazoa':
					# What GBIF calls it
					synonyms['Animalia'] = taxid
				break
				  
		# value of parentid is set by the loop, feeds into the below.

	    # Now process this particular tip.
		# parentid wants to be parent of NCBI taxon, but NCBI taxon might be paraphyletic
		# N.b. we may encounter the same accession number multiple times

		if parentid != None:
			tips += 1
			if not accession in acc_seen:
				acc_seen[accession] = True
			if accession in accession_to_ncbi:
				ncbi = accession_to_ncbi[accession]
				if ncbi == '*':
					blocked = blocked + 1
				else:
					acc_success = acc_success + 1
					if ncbi in ncbi_silva_parent:
						if ncbi_silva_parent[ncbi] != parentid:
							ncbi_silva_parent[ncbi] = None
					else:
						ncbi_silva_parent[ncbi] = parentid
						ncbi_sample_accession[ncbi] = accession
						ncbi_name[ncbi] = path[len(path)-1]
					if ncbi in ncbi_to_accession_unique:
						if ncbi_to_accession_unique[ncbi] != ncbi:
							ncbi_to_accession_unique[ncbi] = None
					else:
						ncbi_to_accession_unique[ncbi] = accession
			else:
				missing.append(accession)

	print "Higher taxa: %d"%internal
	print "Tips: %d"%tips
	print "Accessions: %d  Mapped to NCBI: %d"%(len(acc_seen), len(accession_to_ncbi))
	print "Tip to NCBI taxon mappings: %d successful, %d blocked, %d missing"%(acc_success, blocked, len(missing))

	n2aunique = 0
	for ncbi in ncbi_to_accession_unique:
		if ncbi_to_accession_unique[ncbi] != None:
			n2aunique += 1
	print "NCBI taxa with unique accessions: %s"%(n2aunique)

	name_to_ncbi_unique = {}
	for ncbi in ncbi_name:
		name = ncbi_name[ncbi]
		if name in name_to_ncbi_unique:
			if name_to_ncbi_unique[name] != ncbi:
				name_to_ncbi_unique[name] = None
		else:
			name_to_ncbi_unique[name] = ncbi
			
	nameful = len(ncbi_name)
	uniquely = len(name_to_ncbi_unique)
	print "NCBI taxa: %d  Unambiguous: %d  Ambiguous: %d"%(nameful, uniquely, nameful - uniquely)

	paraphyletic = []
	ncbi_count = 0
	case1 = 0
	case2 = 0
	case3 = 0

	# ncbi_silva_parent maps ncbi id to id of parent in silva

	for ncbi in ncbi_silva_parent.keys():
		parentid = ncbi_silva_parent[ncbi]
		if parentid != None:
			taxid = ncbi_sample_accession[ncbi]    # becomes URL
			rank = 'samples'    # rank will be set from NCBI
			qid = "ncbi:%s" % ncbi
			synonyms[qid] = taxid
			name = ncbi_name[ncbi]
			outfile.write("%s\t|\t%s\t|\t%s\t|\t%s\t|\t%s\t|\t\n" %
						  (taxid, parentid, name, rank, qid))
			ncbi_count = ncbi_count + 1
			# This isn't useful, is it?
			#longname = "%s %s"%(taxname, qid)
			#synonyms[longname] = taxid
			if ncbi in ncbi_to_accession_unique and ncbi_to_accession_unique[ncbi] != None:
				if name in name_to_ncbi_unique and name_to_ncbi_unique[name] != None:
					case1 += 1
				else:
					case2 += 1
			else:
				case3 += 1
		else:
			paraphyletic.append(ncbi)
	print "NCBI taxa incorporated: %d"%(ncbi_count)
	print "Paraphyletic NCBI taxa: %d"%(len(paraphyletic))    #e.g. 1536
	print "Taxa with unambiguous name and unique accession: %s"%(case1)
	print "Taxa with ambiguous name and unique accession: %s"%(case2)
	print "Taxa with multiple accessions: %s"%(case3)

	outfile.close()
	
def do_synonyms(outdir):
	outfile = open(outdir + "/synonyms.tsv","w")
	outfile.write('uid\t|\tname\t|\t\n')
	for name in synonyms.keys():
		taxid = synonyms[name]
		outfile.write("%s\t|\t%s\t|\t\n" % (taxid, name))

def main():
	# was: infile = open('SSURef_NR99_115_tax_silva.fasta','rU')
	indir = sys.argv[1]
	outdir = sys.argv[2]
	url = sys.argv[3]
	fastafilename = indir + '/silva.fasta'
	writeAboutFile(url, fastafilename, outdir)
	readNcbi(indir)
	# readRanks(indir) - no longer used
	pathdict = makePathDict(fastafilename, outdir + '/silva_taxonly.txt')
	processSilva(pathdict, indir, outdir)
	do_synonyms(outdir)
	
main()

# 						if False:
# 							rank_key = (taxname,par)
# 							if rank_key in ranks:
# 								rank = ranks[rank_key].lower()
# 							else:
# 								rank = 'no rank'
# 							if rank == 'major_clade':
# 								rank = 'no rank'
