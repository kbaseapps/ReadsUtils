#include <KBaseCommon.spec>
/*
Utilities for handling reads files.
*/

module ReadsUtils {

    /* A boolean - 0 for false, 1 for true.
       @range (0, 1)
    */
    typedef int boolean;
    
    /* A ternary. Allowed values are 'false', 'true', or null. Any other
        value is invalid.
     */
     typedef string tern;
    
    /* A reference to a read library stored in the workspace service, whether
        of the KBaseAssembly or KBaseFile type. Usage of absolute references
        (e.g. 256/3/6) is strongly encouraged to avoid race conditions,
        although any valid reference is allowed.
    */
    typedef string read_lib;

    /* Input to the validateFASTQ function.
    
        Required parameters:
        file_path - the path to the file to validate.
        
        Optional parameters:
        interleaved - whether the file is interleaved or not. Setting this to
            true disables sequence ID checks.
    */
    typedef structure {
        string file_path;
        boolean interleaved;
    } ValidateFASTQParams;
    
    /* The output of the validateFASTQ function.
        
        validated - whether the file validated successfully or not.
    */
    typedef structure {
        boolean validated;
    } ValidateFASTQOutput;

    /* Validate a FASTQ file. The file extensions .fq, .fnq, and .fastq
        are accepted. Note that prior to validation the file will be altered in
        place to remove blank lines if any exist.
    */
    funcdef validateFASTQ(list<ValidateFASTQParams> params)
        returns(list<ValidateFASTQOutput> out) authentication required;
    
    /* Input to the upload_reads function.
        
        If local files are specified for upload, they must be uncompressed.
        Files will be gzipped prior to upload.
        
        Note that if a reverse read file is specified, it must be a local file
        if the forward reads file is a local file, or a shock id if not.

        If a reverse file is specified the uploader will will automatically
        intereave the forward and reverse files and store that in shock.
        Additionally the statistics generated are on the resulting interleaved file.
        
        Required parameters:
        fwd_id - the id of the shock node containing the reads data file:
            either single end reads, forward/left reads, or interleaved reads.
        - OR -
        fwd_file - a local path to the reads data file: either single end
            reads, forward/left reads, or interleaved reads.
        
        sequencing_tech - the sequencing technology used to produce the
            reads. (If source_reads_ref is specified then sequencing_tech
            must not be specified)

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
        - OR -
        rev_file - a local path to the reads data file containing the
            reverse/right reads for paired end, non-interleaved reads, 
            note the reverse file will get interleaved 
            with the forward file.
        single_genome - whether the reads are from a single genome or a
            metagenome. Default is single genome.
        strain - information about the organism strain
            that was sequenced.
        source - information about the organism source.
        interleaved - specify that the fwd reads file is an interleaved paired
            end reads file as opposed to a single end reads file. Default true,
            ignored if rev_id is specified.
        read_orientation_outward - whether the read orientation is outward
            from the set of primers. Default is false and is ignored for
            single end reads.
        insert_size_mean - the mean size of the genetic fragments. Ignored for
            single end reads.
        insert_size_std_dev - the standard deviation of the size of the
            genetic fragments. Ignored for single end reads.
        source_reads_ref - A workspace reference to a source reads object.
            This is used to propogate user defined info from the source reads
            object to the new reads object (used for filtering or 
            trimming services). Note this causes a passed in 
            insert_size_mean, insert_size_std_dev, sequencing_tech,
            read_orientation_outward, strain, source and/or 
            single_genome to throw an error.
    */
    typedef structure {
        string fwd_id;
        string fwd_file;
        int wsid;
        string wsname;
        int objid;
        string name;
        string rev_id;
        string rev_file;
        string sequencing_tech;
        boolean single_genome;
        KBaseCommon.StrainInfo strain;
        KBaseCommon.SourceInfo source;
        boolean interleaved;
        boolean read_orientation_outward;
        float insert_size_mean;
        float insert_size_std_dev;
        string source_reads_ref;
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
        
   /* Input parameters for downloading reads objects.
        list<read_lib> read_libraries - the the workspace read library objects
            to download.
        tern interleaved - if true, provide the files in interleaved format if
            they are not already. If false, provide forward and reverse reads
            files. If null or missing, leave files as is.
    */
    typedef structure {
        list<read_lib> read_libraries;
        tern interleaved;
    } DownloadReadsParams;
    
    /* Reads file information.
        Note that the file names provided are those *prior to* interleaving
        or deinterleaving the reads.
        
        string fwd - the path to the forward / left reads.
        string fwd_name - the name of the forwards reads file from Shock, or
            if not available, from the Shock handle.
        string rev - the path to the reverse / right reads. null if the reads
            are single end or interleaved.
        string rev_name - the name of the reverse reads file from Shock, or
            if not available, from the Shock handle. null if the reads
            are single end or interleaved.
        string otype - the original type of the reads. One of 'single',
            'paired', or 'interleaved'.
        string type - one of 'single', 'paired', or 'interleaved'.
     */
    typedef structure {
        string fwd;
        string fwd_name;
        string rev;
        string rev_name;
        string otype;
        string type;
    } ReadsFiles;
    
    /* Information about each set of reads.
        ReadsFiles files - the reads files.
        string ref - the absolute workspace reference of the reads file, e.g
            workspace_id/object_id/version.
        tern single_genome - whether the reads are from a single genome or a
            metagenome. null if unknown.
        tern read_orientation_outward - whether the read orientation is outward
            from the set of primers. null if unknown or single ended reads.
        string sequencing_tech - the sequencing technology used to produce the
            reads. null if unknown.
        KBaseCommon.StrainInfo strain - information about the organism strain
            that was sequenced. null if unavailable.
        KBaseCommon.SourceInfo source - information about the organism source.
            null if unavailable.
        float insert_size_mean - the mean size of the genetic fragments. null
            if unavailable or single end reads.
        float insert_size_std_dev - the standard deviation of the size of the
            genetic fragments. null if unavailable or single end reads.
        int read_count - the number of reads in the this dataset. null if
            unavailable.
        int read_size - sequencing parameter defining the expected read length. 
            For paired end reads, this is the expected length of the total of 
            the two reads. null if unavailable.
        float gc_content - the GC content of the reads. null if
            unavailable.
        int total_bases - The total number of bases in all the reads
        float read_length_mean - The mean read length. null if unavailable.
        float read_length_stdev - The std dev of read length. null if unavailable.
        string phred_type - Phred type: 33 or 64. null if unavailable.
        int number_of_duplicates - Number of duplicate reads. null if unavailable.
        float qual_min - Minimum Quality Score. null if unavailable.
        float qual_max - Maximum Quality Score. null if unavailable.
        float qual_mean - Mean Quality Score. null if unavailable.
        float qual_stdev - Std dev of Quality Scores. null if unavailable.
        mapping<string, float> base_percentages - percentage of total bases being 
            a particular nucleotide.  Null if unavailable.
     */
    typedef structure {
        ReadsFiles files;
        string ref;
        tern single_genome;
        tern read_orientation_outward;
        string sequencing_tech;
        KBaseCommon.StrainInfo strain;
        KBaseCommon.SourceInfo source;
        float insert_size_mean;
        float insert_size_std_dev;
        int read_count;
        int read_size;
        float gc_content;
        int total_bases;
        float read_length_mean;
        float read_length_stdev;
        string phred_type;
        int number_of_duplicates;
        float qual_min;
        float qual_max;
        float qual_mean;
        float qual_stdev;
        mapping<string, float> base_percentages;
    } DownloadedReadLibrary;

    /* The output of the download method.
        mapping<read_lib, DownloadedReadLibrary> files - a mapping
            of the read library workspace references to information
            about the converted data for each library.
     */
    typedef structure {
        mapping<read_lib, DownloadedReadLibrary> files;
    } DownloadReadsOutput;
   
    /* Download read libraries. Reads compressed with gzip or bzip are
        automatically uncompressed.
     */
    funcdef download_reads(DownloadReadsParams params)
        returns(DownloadReadsOutput output) authentication required;

    /*  Standard KBase downloader input. */
    typedef structure {
        string input_ref;
    } ExportParams;

	/*  Standard KBase downloader output. */
    typedef structure {
        string shock_id;
    } ExportOutput;

    /* KBase downloader function. Packages a set of reads into a zip file and
        stores the zip in shock.
     */
    funcdef export_reads(ExportParams params)
                returns (ExportOutput output) authentication required;
};
