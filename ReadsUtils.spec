#include <KBaseCommon.spec>
/*
Utilities for handling reads files.
*/

module ReadsUtils {

    /* A boolean - 0 for false, 1 for true.
       @range (0, 1)
    */
    typedef int boolean;

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
        
        Required parameters:
        fwd_id - the id of the shock node containing the reads data file:
            either single end reads, forward/left reads, or interleaved reads.
        sequencing_tech - the sequencing technology used to produce the
            reads.
        
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
    */
    typedef structure {
        string fwd_id;
        int wsid;
        string wsname;
        int objid;
        string name;
        string rev_id;
        string sequencing_tech;
        boolean single_genome;
        KBaseCommon.StrainInfo strain;
        KBaseCommon.SourceInfo source;
        boolean interleaved;
        boolean read_orientation_outward;
        float insert_size_mean;
        float insert_size_std_dev;
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

    /* A boolean. Allowed values are 'false' or 'true'. Any other value is
        invalid. */
    typedef string sbool;

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
    
    /* Input parameters for converting libraries to files.
        list<read_lib> read_libraries - the names of the workspace read library
            objects to convert.
        tern gzip - if true, gzip any unzipped files. If false, gunzip any
            zipped files. If null or missing, leave files as is unless
            unzipping is required for interleaving or deinterleaving, in which
            case the files will be left unzipped.
        tern interleaved - if true, provide the files in interleaved format if
            they are not already. If false, provide forward and reverse reads
            files. If null or missing, leave files as is.
    */
    typedef structure {
        list<read_lib> read_libraries;
        tern gzip;
        tern interleaved;
    } ConvertReadLibraryParams;
    
    /* Reads file locations and gzip status.
        Only the relevant fields will be present in the structure.
        string fwd - the path to the forward / left reads.
        string rev - the path to the reverse / right reads.
        string inter - the path to the interleaved reads.
        string sing - the path to the single end reads.
        bool fwd_gz - whether the forward / left reads are gzipped.
        bool rev_gz - whether the reverse / right reads are gzipped.
        bool inter_gz - whether the interleaved reads are gzipped.
        bool sing_gz - whether the single reads are gzipped.
     */
    typedef structure {
        string fwd;
        string rev;
        string inter;
        string sing;
        sbool fwd_gz;
        sbool rev_gz;
        sbool inter_gz;
        sbool sing_gz;
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
        int read_size - the total size of the reads, in bases. null if
            unavailable.
        float gc_content - the GC content of the reads. null if
            unavailable.
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
    } ConvertedReadLibrary;

    /* The output of the convert method.
        mapping<read_lib, ConvertedReadLibrary> files - a mapping
            of the read library workspace references to information
            about the converted data for each library.
     */
    typedef structure {
        mapping<read_lib, ConvertedReadLibrary> files;
    } ConvertReadLibraryOutput;
   
    /* Convert read libraries to files */
    funcdef convert_read_library_to_file(ConvertReadLibraryParams params)
        returns(ConvertReadLibraryOutput output) authentication required;


    typedef structure {
        string input_ref;
    } ExportParams;

    typedef structure {
        string shock_id;
    } ExportOutput;

    /* 
        Using the convert_read_library_to_file function, this prepares a standard
        KBase download package, zips it, and uploads to shock.
    */
    funcdef export_reads(ExportParams params)
        returns(ExportOutput output) authentication required;

};
