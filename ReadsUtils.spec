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
        are accepted.
    */
    funcdef validateFASTQ(string file_path) returns(boolean validated)
        authentication required;
};
