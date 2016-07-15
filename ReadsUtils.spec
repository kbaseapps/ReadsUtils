#include <KBaseCommon.spec>
/*
Utilities for handling reads files.
*/

module ReadsUtils {

    /* A boolean - 0 for false, 1 for true.
       @range (0, 1)
    */
    typedef int boolean;

    /* Validate a FASTA file. The file extensions .fa, .fas, .fna. and .fasta
        are accepted.
    */
    funcdef validateFASTA(string file_path) returns(boolean validated)
        authentication required;
    
    /* Validate a FASTQ file. The file extensions .fq, .fnq, and .fastq
        are accepted. Note that prior to validation the file will be altered in
        place to remove blank lines if any exist.
    */
    funcdef validateFASTQ(string file_path) returns(boolean validated)
        authentication required;
    
    /* Input to the upload_reads function.
        
        Required parameters:
        fwd_id - the id of the shock node containing the reads data file:
            either single end reads, forward/left reads, or interleaved reads.
        
        One of:
        wsid - the id of the workspace where the reads will be saved
            (preferred).
        wsname - the name of the workspace where the reads will be saved.
        
        One of:
        objid - the id of the workspace object to save over
        name - the name to which the workspace object will be saved
            
        Optional parameters:
        rev_id - the shock node id containing the reverse/right reads for
            paired end, non-interleaved reads.
        interleaved - specify that the fwd reads file is an interleaved paired
            end reads file. Default true, ignored if rev is specified.
        single_genome - whether the reads are from a single genome or a
            metagenome. Default is single genome.
        read_orientation_outward - whether the read orientation is outward
            from the set of primers. Default is false and is ignored for
            single end reads.
        sequencing_tech - the sequencing technology used to produce the
            reads.
        strain - information about the organism strain
            that was sequenced.
        source - information about the organism source.
        insert_size_mean - the mean size of the genetic fragments. Ignored for
            single end reads.
        insert_size_std_dev - the standard deviation of the size of the
            genetic fragments. Ignored for single end reads.
        read_count - the number of reads in the this dataset.
        read_size - the total size of the reads, in bases.
        gc_content - the GC content of the reads.
    */
    typedef structure {
        string fwd_id;
        int wsid;
        string wsname;
        int objid;
        string name;
        string rev_id;
        boolean interleaved;
        boolean single_genome;
        boolean read_orientation_outward;
        string sequencing_tech;
        KBaseCommon.StrainInfo strain;
        KBaseCommon.SourceInfo source;
        float insert_size_mean;
        float insert_size_std_dev;
        int read_count;
        int read_size;
        float gc_content;
    } UploadReadsParams;
    
    /* The output of the upload_reads function.
    
        obj_ref - a reference to the new Workspace object in the form X/Y/Z,
            where X is the workspace ID, Y is the object ID, and Z is the
            version.
    */
    typedef structure {
        string obj_ref;
    } UploadReadsOutput;
    
    /* Loads a set of reads to KBase data stores. */
    funcdef upload_reads(UploadReadsParams params) returns(UploadReadsOutput)
        authentication required;
};
