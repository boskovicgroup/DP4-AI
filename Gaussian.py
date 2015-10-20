#!/usr/bin/env python
from __future__ import division
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 19 15:56:54 2014

@author: ke291

Contains all of the Gaussian specific code for input generation and calculation
execution. Called by PyDP4.py.
"""

import Tinker
import MacroModel
import nmrPredictGaus

import subprocess
import socket
import os
import time
import sys
import glob
import pyximport
pyximport.install()
import ConfPrune


def SetupGaussian(MMoutp, Gausinp, numDigits, settings, adjRMSDcutoff):

    if settings.MMTinker:
        #Reads conformer geometry, energies and atom labels from Tinker output
        (atoms, conformers, charge) = Tinker.ReadTinker(MMoutp, settings)
    else:
        (atoms, conformers, charge) = MacroModel.ReadMacromodel(MMoutp,
                                                                settings)

    #Prune similar conformations, if the number exceeds the limit
    if len(conformers) > settings.PerStructConfLimit and settings.ConfPrune:
        pruned = ConfPrune.RMSDPrune(conformers, atoms, adjRMSDcutoff)
    else:
        pruned = conformers

    if settings.ConfPrune:
        print str(len(conformers) - len(pruned)) +\
            " or " + "{:.1f}".format(100*(len(conformers) - len(pruned)) /
            len(conformers))+"% of conformations have been pruned based on " +\
            str(adjRMSDcutoff) + " angstrom cutoff"

    for num in range(0, len(pruned)):
        filename = Gausinp+str(num+1).zfill(3)
        if not settings.DFTOpt:
            WriteGausFile(filename, pruned[num], atoms, charge, settings)
        else:
            WriteGausFileOpt(filename, pruned[num], atoms, charge, settings)

    print str(len(pruned)) + " .com files written"


#Adjust the RMSD cutoff to keep the conformation numbers reasonable
def AdaptiveRMSD(MMoutp, settings):

    if settings.MMTinker:
        #Reads conformer geometry, energies and atom labels from Tinker output
        (atoms, conformers, charge) = Tinker.ReadTinker(MMoutp, settings)
    else:
        (atoms, conformers, charge) = MacroModel.ReadMacromodel(MMoutp,
                                                                settings)

    return ConfPrune.AdaptRMSDPrune(conformers, atoms,
                                    settings.InitialRMSDcutoff,
                                    settings.PerStructConfLimit)


def WriteGausFile(Gausinp, conformer, atoms, charge, settings):

    f = file(Gausinp + '.com', 'w')
    f.write('%mem=6000MB\n%chk='+Gausinp + '.chk\n')
    
    if (settings.Functional).lower() == 'wp04':
        CompSettings = '# blyp/' + settings.BasisSet +\
            ' iop(3/76=1000001189,3/77=0961409999,3/78=0000109999)' + \
            ' nmr='
    elif (settings.Functional).lower() == 'm062x':
        CompSettings = '# ' + settings.Functional + '/' + settings.BasisSet +\
            ' int=ultrafine nmr='
    else:
        CompSettings = '# ' + settings.Functional + '/' + settings.BasisSet +\
            ' nmr='
    
    if settings.jJ or settings.jFC:
        CompSettings += '(giao,spinspin,mixed)'
    else:
        CompSettings += 'giao'
    
    if settings.Solvent != '':
        CompSettings += ' scrf=(solvent=' + settings.Solvent+')\n'
        #f.write('# b3lyp/6-31g(d,p) nmr=giao scrf=(solvent=' +
        #        settings.Solvent+')\n')
    else:
        CompSettings += '\n'
        #f.write('# b3lyp/6-31g(d,p) nmr=giao\n')
    f.write(CompSettings)
    f.write('\n'+Gausinp+'\n\n')
    f.write(str(charge) + ' 1\n')

    natom = 0

    for atom in conformer:
        f.write(atoms[natom] + '  ' + atom[1] + '  ' + atom[2] + '  ' +
                atom[3] + '\n')
        natom = natom + 1
    f.write('\n')
    f.close()


def WriteGausFileOpt(Gausinp, conformer, atoms, charge, settings):

    #write the initial DFT geometry optimisation input file first
    f1 = file(Gausinp + 'a.com', 'w')
    f1.write('%mem=6000MB\n%chk='+Gausinp + '.chk\n')

    if settings.Solvent != '':
        f1.write('# b3lyp/6-31g(d,p) Opt=(maxcycles=30) scrf=(solvent=' +
                 settings.Solvent+')\n')
    else:
        f1.write('# b3lyp/6-31g(d,p) Opt=(maxcycles=30)\n')

    f1.write('\n'+Gausinp+'\n\n')
    f1.write(str(charge) + ' 1\n')

    natom = 0

    for atom in conformer:
        f1.write(atoms[natom] + '  ' + atom[1] + '  ' + atom[2] + '  ' +
                 atom[3] + '\n')
        natom = natom + 1
    f1.write('\n')
    f1.close()

    #Write the nmr prediction input file,
    #using the geometry from checkpoint file
    f2 = file(Gausinp + 'b.com', 'w')
    f2.write('%mem=6000MB\n%chk='+Gausinp + '.chk\n')
    if (settings.Functional).lower() == 'wp04':
        CompSettings = '# blyp/' + settings.BasisSet +\
            ' iop(3/76=1000001189,3/77=0961409999,3/78=0000109999)' + \
            ' geom=checkpoint nmr='
    elif (settings.Functional).lower() == 'm062x':
        CompSettings = '# ' + settings.Functional + '/' + settings.BasisSet +\
            ' int=ultrafine geom=checkpoint nmr='
    else:
        CompSettings = '# ' + settings.Functional + '/' + settings.BasisSet +\
            ' geom=checkpoint nmr='
    
    if settings.jJ or settings.jFC:
        CompSettings += '(giao,spinspin,mixed)'
    else:
        CompSettings += 'giao'
    
    if settings.Solvent != '':
        CompSettings += ' scrf=(solvent=' + settings.Solvent+')\n'
        #f.write('# b3lyp/6-31g(d,p) nmr=giao scrf=(solvent=' +
        #        settings.Solvent+')\n')
    else:
        CompSettings += '\n'
        #f.write('# b3lyp/6-31g(d,p) nmr=giao\n')
    f2.write(CompSettings)
    f2.write('\n'+Gausinp+'\n\n')
    f2.write(str(charge) + ' 1\n')
    f2.write('\n')
    f2.close()


def GetFiles2Run(inpfiles, settings):
    #Get the names of all relevant input files
    GinpFiles = []
    for filename in inpfiles:
        if not settings.DFTOpt:
            GinpFiles = GinpFiles + glob.glob(filename + 'ginp???.com')
        else:
            GinpFiles = GinpFiles + glob.glob(filename + 'ginp???a.com')
    Files2Run = []

    #for every input file check that there is a completed output file,
    #delete the incomplete outputs and add the inputs to be done to Files2Run
    for filename in GinpFiles:
        if not settings.DFTOpt:
            if not os.path.exists(filename[:-3]+'out'):
                Files2Run.append(filename)
            else:
                if IsGausCompleted(filename[:-3] + 'out'):
                    #print filename[:-3]+'out already exists'
                    continue
                else:
                    os.remove(filename[:-3] + 'out')
                    Files2Run.append(filename)
        else:
            if not os.path.exists(filename[:-5]+'.out'):
                Files2Run.append(filename)
            else:
                if IsGausCompleted(filename[:-5] + '.out'):
                    #print filename[:-3]+'out already exists'
                    continue
                else:
                    os.remove(filename[:-5] + '.out')
                    Files2Run.append(filename)

    return Files2Run


def IsGausCompleted(f):
    Gfile = open(f, 'r')
    outp = Gfile.readlines()
    Gfile.close()
    if len(outp) < 10:
        return False
    if "Normal termination" in outp[-1]:
        return True
    else:
        return False


#Still need addition of support for geometry optimisation
def RunOnZiggy(folder, queue, GausFiles, settings):

    print "ziggy GAUSSIAN job submission script\n"

    #Check that folder does not exist, create job folder on ziggy
    outp = subprocess.check_output('ssh ziggy ls', shell=True)
    if folder in outp:
        print "Folder exists on ziggy, choose another folder name."
        return

    outp = subprocess.check_output('ssh ziggy mkdir ' + folder, shell=True)

    #Write the qsub scripts
    for f in GausFiles:
        if not settings.DFTOpt:
            WriteSubScript(f[:-4], queue, folder, settings)
        else:
            WriteSubScriptOpt(f[:-4], queue, folder, settings)
    print str(len(GausFiles)) + ' .qsub scripts generated'

    #Upload .com files and .qsub files to directory
    print "Uploading files to ziggy..."
    for f in GausFiles:
        if not settings.DFTOpt:
            outp = subprocess.check_output('scp ' + f +' ziggy:~/' + folder,
                                           shell=True)
        else:
            outp = subprocess.check_output('scp ' + f[:-4] +'a.com ziggy:~/' +
                                           folder, shell=True)
            outp = subprocess.check_output('scp ' + f[:-4] +'b.com ziggy:~/' +
                                           folder, shell=True)
        outp = subprocess.check_output('scp ' + f[:-4] +'.qsub ziggy:~/' +
                                       folder, shell=True)

    print str(len(GausFiles)) + ' .com and .qsub files uploaded to ziggy'

    #Launch the calculations
    for f in GausFiles:
        job = '~/' + folder + '/' + f[:-4]
        outp = subprocess.check_output('ssh ziggy qsub -q ' + queue + ' -o ' +
            job + '.log -e ' + job + '.err ' + job + '.qsub', shell=True)

    print str(len(GausFiles)) + ' jobs submitted to the queue on ziggy'

    outp = subprocess.check_output('ssh ziggy showq', shell=True)
    if settings.user in outp:
        print "Jobs are running on ziggy"

    Jobs2Complete = list(GausFiles)
    n2complete = len(Jobs2Complete)

    #Check and report on the progress of calculations
    while len(Jobs2Complete) > 0:
        JustCompleted = [job for job in Jobs2Complete if
            IsZiggyGComplete(job[:-3] + 'out', folder, settings)]
        Jobs2Complete[:] = [job for job in Jobs2Complete if
             not IsZiggyGComplete(job[:-3] + 'out', folder, settings)]
        if n2complete != len(Jobs2Complete):
            n2complete = len(Jobs2Complete)
            print str(n2complete) + " remaining."

        time.sleep(60)

    #When done, copy the results back
    print "\nCopying the output files back to localhost..."
    print 'ssh ziggy scp /home/' + settings.user + '/' + folder + '/*.out ' +\
        socket.getfqdn() + ':' + os.getcwd()
    outp = subprocess.check_output('ssh ziggy scp /home/' + settings.user +
                                   '/' + folder + '/*.out ' + socket.getfqdn()
                                   + ':' + os.getcwd(), shell=True)


def WriteSubScript(GausJob, queue, ZiggyJobFolder, settings):

    if not (os.path.exists(GausJob+'.com')):
        print "The input file " + GausJob + ".com does not exist. Exiting..."
        return

    #Create the submission script
    QSub = open(GausJob + ".qsub", 'w')

    #Choose the queue
    QSub.write('#PBS -q ' + queue + '\n#PBS -l nodes=1:ppn=1\n#\n')

    #define input files and output files
    QSub.write('file=' + GausJob + '\n\n')
    QSub.write('inpfile=${file}.com\noutfile=${file}.out\n')

    #define cwd and scratch folder and ask the machine
    #to make it before running the job
    QSub.write('HERE=/home/' + settings.user +'/' + ZiggyJobFolder + '\n')
    QSub.write('LSCRATCH=/scratch/' + settings.user + '/' +
               GausJob + '\n')
    QSub.write('mkdir ${LSCRATCH}\n')

    #Setup GAUSSIAN environment variables
    QSub.write('set OMP_NUM_THREADS=1\n')
    QSub.write('export GAUSS_EXEDIR=/usr/local/shared/gaussian/em64t/09-D01/g09\n')
    QSub.write('export g09root=/usr/local/shared/gaussian/em64t/09-D01\n')
    QSub.write('export PATH=/usr/local/shared/gaussian/em64t/09-D01/g09:$PATH\n')
    QSub.write('export GAUSS_SCRDIR=$LSCRATCH\n')

    #copy the input file to scratch
    QSub.write('cp ${HERE}/${inpfile}  $LSCRATCH\ncd $LSCRATCH\n')

    #write useful info to the job output file (not the gaussian)
    QSub.write('echo "Starting job $PBS_JOBID"\necho\n')
    QSub.write('echo "PBS assigned me this node:"\ncat $PBS_NODEFILE\necho\n')

    QSub.write('ln -s $HERE/$outfile $LSCRATCH/$outfile\n')
    QSub.write('$GAUSS_EXEDIR/g09 < $inpfile > $outfile\n')

    #Cleanup
    QSub.write('rm -rf ${LSCRATCH}/\n')
    QSub.write('qstat -f $PBS_JOBID\n')

    QSub.close()

#Function to write ziggy script when dft optimisation is used
def WriteSubScriptOpt(GausJob, queue, ZiggyJobFolder, settings):

    if not (os.path.exists(GausJob+'a.com')):
        print "The input file " + GausJob + "a.com does not exist. Exiting..."
        return
    if not (os.path.exists(GausJob+'b.com')):
        print "The input file " + GausJob + "b.com does not exist. Exiting..."
        return

    #Create the submission script
    QSub = open(GausJob + ".qsub", 'w')

    #Choose the queue
    QSub.write('#PBS -q ' + queue + '\n#PBS -l nodes=1:ppn=1\n#\n')

    #define input files and output files
    QSub.write('file=' + GausJob + '\n\n')
    QSub.write('inpfile1=${file}a.com\ninpfile2=${file}b.com\n')
    QSub.write('outfile1=${file}temp.out\noutfile2=${file}.out\n')

    #define cwd and scratch folder and ask the machine
    #to make it before running the job
    QSub.write('HERE=/home/' + settings.user +'/' + ZiggyJobFolder + '\n')
    QSub.write('SCRATCH=/sharedscratch/' + settings.user + '/' + GausJob + ZiggyJobFolder +'\n')
    QSub.write('mkdir ${SCRATCH}\n')

    #Setup GAUSSIAN environment variables
    QSub.write('set OMP_NUM_THREADS=1\n')
    QSub.write('export GAUSS_EXEDIR=/usr/local/shared/gaussian/em64t/09-D01/g09\n')
    QSub.write('export g09root=/usr/local/shared/gaussian/em64t/09-D01\n')
    QSub.write('export PATH=/usr/local/shared/gaussian/em64t/09-D01/g09:$PATH\n')
    QSub.write('export GAUSS_SCRDIR=$SCRATCH\n')

    #copy the input files to scratch
    QSub.write('cp ${HERE}/${inpfile1}  $SCRATCH\n')
    QSub.write('cp ${HERE}/${inpfile2}  $SCRATCH\ncd $SCRATCH\n')

    #write useful info to the job output file (not the gaussian)
    QSub.write('echo "Starting job $PBS_JOBID"\necho\n')
    QSub.write('echo "PBS assigned me this node:"\ncat $PBS_NODEFILE\necho\n')

    QSub.write('ln -s $HERE/$outfile2 $SCRATCH/$outfile2\n')
    QSub.write('$GAUSS_EXEDIR/g09 < $inpfile1 > $outfile1\n')
    QSub.write('$GAUSS_EXEDIR/g09 < $inpfile2 > $outfile2\n')

    #Cleanup
    QSub.write('mkdir ${HERE}/${file}\n')
    QSub.write('cp ${SCRATCH}/*.chk  $HERE/${file}/\n')
    QSub.write('rm -f ${SCRATCH}/*\n')
    QSub.write('cp $HERE/${file}/*.chk ${SCRATCH}/\n')
    QSub.write('rm -r ${HERE}/${file}\n')
    QSub.write('qstat -f $PBS_JOBID\n')

    QSub.close()


def IsZiggyGComplete(f, folder, settings):

    path = '/home/' + settings.user + '/' + folder + '/'
    try:
        outp1 = subprocess.check_output('ssh ziggy ls ' + path, shell=True)
    except subprocess.CalledProcessError, e:
        print "ssh ziggy ls failed: " + str(e.output)
        return False
    if f in outp1:
        try:
            outp2 = subprocess.check_output('ssh ziggy cat ' + path + f,
                                            shell=True)
        except subprocess.CalledProcessError, e:
            print "ssh ziggy cat failed: " + str(e.output)
            return False
        if "Normal termination" in outp2[-90:]:
            return True
    return False


def RunNMRPredict(numDS, settings, *args):

    GausNames = []
    NTaut = []

    for val in range(0, numDS):
        NTaut.append(args[val*2])
        GausNames.append(args[val*2+1])

    RelEs = []
    populations = []
    BoltzmannShieldings = []
    BoltzmannJs = []
    BoltzmannFCs = []

    print GausNames
    print NTaut
    #This loop runs nmrPredict for each diastereomer and collects
    #the outputs    
    for isomer in GausNames:

        GausFiles = glob.glob(isomer + 'ginp*.out')
        GausFiles = [x[:-4] for x in GausFiles]
        
        #Runs nmrPredictGaus Name001, ... and collects output
        Es, Pops, ls, BSs, Jls, BFCs, BJs = nmrPredictGaus.main(settings,
                                                                *GausFiles)
        RelEs.append(Es)
        populations.append(Pops)
        BoltzmannShieldings.append(BSs)
        BoltzmannFCs.append(BFCs)
        BoltzmannJs.append(BJs)

    return (RelEs, populations, ls, BoltzmannShieldings, Jls, BoltzmannFCs,
            BoltzmannJs, NTaut)


def getScriptPath():
    return os.path.dirname(os.path.realpath(sys.argv[0]))
