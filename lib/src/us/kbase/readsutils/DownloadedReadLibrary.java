
package us.kbase.readsutils;

import java.util.HashMap;
import java.util.Map;
import javax.annotation.Generated;
import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;
import us.kbase.kbasecommon.SourceInfo;
import us.kbase.kbasecommon.StrainInfo;


/**
 * <p>Original spec-file type: DownloadedReadLibrary</p>
 * <pre>
 * Information about each set of reads.
 * ReadsFiles files - the reads files.
 * string ref - the absolute workspace reference of the reads file, e.g
 *     workspace_id/object_id/version.
 * tern single_genome - whether the reads are from a single genome or a
 *     metagenome. null if unknown.
 * tern read_orientation_outward - whether the read orientation is outward
 *     from the set of primers. null if unknown or single ended reads.
 * string sequencing_tech - the sequencing technology used to produce the
 *     reads. null if unknown.
 * KBaseCommon.StrainInfo strain - information about the organism strain
 *     that was sequenced. null if unavailable.
 * KBaseCommon.SourceInfo source - information about the organism source.
 *     null if unavailable.
 * float insert_size_mean - the mean size of the genetic fragments. null
 *     if unavailable or single end reads.
 * float insert_size_std_dev - the standard deviation of the size of the
 *     genetic fragments. null if unavailable or single end reads.
 * int read_count - the number of reads in the this dataset. null if
 *     unavailable.
 * int read_size - sequencing parameter defining the expected read length. 
 *     For paired end reads, this is the expected length of the total of 
 *     the two reads. null if unavailable.
 * float gc_content - the GC content of the reads. null if
 *     unavailable.
 * int total_bases - The total number of bases in all the reads
 * float read_length_mean - The mean read length. null if unavailable.
 * float read_length_stdev - The std dev of read length. null if unavailable.
 * string phred_type - Phred type: 33 or 64. null if unavailable.
 * int number_of_duplicates - Number of duplicate reads. null if unavailable.
 * float qual_min - Minimum Quality Score. null if unavailable.
 * float qual_max - Maximum Quality Score. null if unavailable.
 * float qual_mean - Mean Quality Score. null if unavailable.
 * float qual_stdev - Std dev of Quality Scores. null if unavailable.
 * mapping<string, float> base_percentages - percentage of total bases being 
 *     a particular nucleotide.  Null if unavailable.
 * </pre>
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@Generated("com.googlecode.jsonschema2pojo")
@JsonPropertyOrder({
    "files",
    "ref",
    "single_genome",
    "read_orientation_outward",
    "sequencing_tech",
    "strain",
    "source",
    "insert_size_mean",
    "insert_size_std_dev",
    "read_count",
    "read_size",
    "gc_content",
    "total_bases",
    "read_length_mean",
    "read_length_stdev",
    "phred_type",
    "number_of_duplicates",
    "qual_min",
    "qual_max",
    "qual_mean",
    "qual_stdev",
    "base_percentages"
})
public class DownloadedReadLibrary {

    /**
     * <p>Original spec-file type: ReadsFiles</p>
     * <pre>
     * Reads file information.
     * Note that the file names provided are those *prior to* interleaving
     * or deinterleaving the reads.
     * string fwd - the path to the forward / left reads.
     * string fwd_name - the name of the forwards reads file from Shock, or
     *     if not available, from the Shock handle.
     * string rev - the path to the reverse / right reads. null if the reads
     *     are single end or interleaved.
     * string rev_name - the name of the reverse reads file from Shock, or
     *     if not available, from the Shock handle. null if the reads
     *     are single end or interleaved.
     * string otype - the original type of the reads. One of 'single',
     *     'paired', or 'interleaved'.
     * string type - one of 'single', 'paired', or 'interleaved'.
     * </pre>
     * 
     */
    @JsonProperty("files")
    private ReadsFiles files;
    @JsonProperty("ref")
    private java.lang.String ref;
    @JsonProperty("single_genome")
    private java.lang.String singleGenome;
    @JsonProperty("read_orientation_outward")
    private java.lang.String readOrientationOutward;
    @JsonProperty("sequencing_tech")
    private java.lang.String sequencingTech;
    /**
     * <p>Original spec-file type: StrainInfo</p>
     * <pre>
     * Information about a strain.
     * genetic_code - the genetic code of the strain.
     *     See http://www.ncbi.nlm.nih.gov/Taxonomy/Utils/wprintgc.cgi?mode=c
     * genus - the genus of the strain
     * species - the species of the strain
     * strain - the identifier for the strain
     * source - information about the source of the strain
     * organelle - the organelle of interest for the related data (e.g.
     *     mitochondria)
     * ncbi_taxid - the NCBI taxonomy ID of the strain
     * location - the location from which the strain was collected
     * @optional genetic_code source ncbi_taxid organelle location
     * </pre>
     * 
     */
    @JsonProperty("strain")
    private StrainInfo strain;
    /**
     * <p>Original spec-file type: SourceInfo</p>
     * <pre>
     * Information about the source of a piece of data.
     * source - the name of the source (e.g. NCBI, JGI, Swiss-Prot)
     * source_id - the ID of the data at the source
     * project_id - the ID of a project encompassing the data at the source
     * @optional source source_id project_id
     * </pre>
     * 
     */
    @JsonProperty("source")
    private SourceInfo source;
    @JsonProperty("insert_size_mean")
    private java.lang.Double insertSizeMean;
    @JsonProperty("insert_size_std_dev")
    private java.lang.Double insertSizeStdDev;
    @JsonProperty("read_count")
    private Long readCount;
    @JsonProperty("read_size")
    private Long readSize;
    @JsonProperty("gc_content")
    private java.lang.Double gcContent;
    @JsonProperty("total_bases")
    private Long totalBases;
    @JsonProperty("read_length_mean")
    private java.lang.Double readLengthMean;
    @JsonProperty("read_length_stdev")
    private java.lang.Double readLengthStdev;
    @JsonProperty("phred_type")
    private java.lang.String phredType;
    @JsonProperty("number_of_duplicates")
    private Long numberOfDuplicates;
    @JsonProperty("qual_min")
    private java.lang.Double qualMin;
    @JsonProperty("qual_max")
    private java.lang.Double qualMax;
    @JsonProperty("qual_mean")
    private java.lang.Double qualMean;
    @JsonProperty("qual_stdev")
    private java.lang.Double qualStdev;
    @JsonProperty("base_percentages")
    private Map<String, Double> basePercentages;
    private Map<java.lang.String, Object> additionalProperties = new HashMap<java.lang.String, Object>();

    /**
     * <p>Original spec-file type: ReadsFiles</p>
     * <pre>
     * Reads file information.
     * Note that the file names provided are those *prior to* interleaving
     * or deinterleaving the reads.
     * string fwd - the path to the forward / left reads.
     * string fwd_name - the name of the forwards reads file from Shock, or
     *     if not available, from the Shock handle.
     * string rev - the path to the reverse / right reads. null if the reads
     *     are single end or interleaved.
     * string rev_name - the name of the reverse reads file from Shock, or
     *     if not available, from the Shock handle. null if the reads
     *     are single end or interleaved.
     * string otype - the original type of the reads. One of 'single',
     *     'paired', or 'interleaved'.
     * string type - one of 'single', 'paired', or 'interleaved'.
     * </pre>
     * 
     */
    @JsonProperty("files")
    public ReadsFiles getFiles() {
        return files;
    }

    /**
     * <p>Original spec-file type: ReadsFiles</p>
     * <pre>
     * Reads file information.
     * Note that the file names provided are those *prior to* interleaving
     * or deinterleaving the reads.
     * string fwd - the path to the forward / left reads.
     * string fwd_name - the name of the forwards reads file from Shock, or
     *     if not available, from the Shock handle.
     * string rev - the path to the reverse / right reads. null if the reads
     *     are single end or interleaved.
     * string rev_name - the name of the reverse reads file from Shock, or
     *     if not available, from the Shock handle. null if the reads
     *     are single end or interleaved.
     * string otype - the original type of the reads. One of 'single',
     *     'paired', or 'interleaved'.
     * string type - one of 'single', 'paired', or 'interleaved'.
     * </pre>
     * 
     */
    @JsonProperty("files")
    public void setFiles(ReadsFiles files) {
        this.files = files;
    }

    public DownloadedReadLibrary withFiles(ReadsFiles files) {
        this.files = files;
        return this;
    }

    @JsonProperty("ref")
    public java.lang.String getRef() {
        return ref;
    }

    @JsonProperty("ref")
    public void setRef(java.lang.String ref) {
        this.ref = ref;
    }

    public DownloadedReadLibrary withRef(java.lang.String ref) {
        this.ref = ref;
        return this;
    }

    @JsonProperty("single_genome")
    public java.lang.String getSingleGenome() {
        return singleGenome;
    }

    @JsonProperty("single_genome")
    public void setSingleGenome(java.lang.String singleGenome) {
        this.singleGenome = singleGenome;
    }

    public DownloadedReadLibrary withSingleGenome(java.lang.String singleGenome) {
        this.singleGenome = singleGenome;
        return this;
    }

    @JsonProperty("read_orientation_outward")
    public java.lang.String getReadOrientationOutward() {
        return readOrientationOutward;
    }

    @JsonProperty("read_orientation_outward")
    public void setReadOrientationOutward(java.lang.String readOrientationOutward) {
        this.readOrientationOutward = readOrientationOutward;
    }

    public DownloadedReadLibrary withReadOrientationOutward(java.lang.String readOrientationOutward) {
        this.readOrientationOutward = readOrientationOutward;
        return this;
    }

    @JsonProperty("sequencing_tech")
    public java.lang.String getSequencingTech() {
        return sequencingTech;
    }

    @JsonProperty("sequencing_tech")
    public void setSequencingTech(java.lang.String sequencingTech) {
        this.sequencingTech = sequencingTech;
    }

    public DownloadedReadLibrary withSequencingTech(java.lang.String sequencingTech) {
        this.sequencingTech = sequencingTech;
        return this;
    }

    /**
     * <p>Original spec-file type: StrainInfo</p>
     * <pre>
     * Information about a strain.
     * genetic_code - the genetic code of the strain.
     *     See http://www.ncbi.nlm.nih.gov/Taxonomy/Utils/wprintgc.cgi?mode=c
     * genus - the genus of the strain
     * species - the species of the strain
     * strain - the identifier for the strain
     * source - information about the source of the strain
     * organelle - the organelle of interest for the related data (e.g.
     *     mitochondria)
     * ncbi_taxid - the NCBI taxonomy ID of the strain
     * location - the location from which the strain was collected
     * @optional genetic_code source ncbi_taxid organelle location
     * </pre>
     * 
     */
    @JsonProperty("strain")
    public StrainInfo getStrain() {
        return strain;
    }

    /**
     * <p>Original spec-file type: StrainInfo</p>
     * <pre>
     * Information about a strain.
     * genetic_code - the genetic code of the strain.
     *     See http://www.ncbi.nlm.nih.gov/Taxonomy/Utils/wprintgc.cgi?mode=c
     * genus - the genus of the strain
     * species - the species of the strain
     * strain - the identifier for the strain
     * source - information about the source of the strain
     * organelle - the organelle of interest for the related data (e.g.
     *     mitochondria)
     * ncbi_taxid - the NCBI taxonomy ID of the strain
     * location - the location from which the strain was collected
     * @optional genetic_code source ncbi_taxid organelle location
     * </pre>
     * 
     */
    @JsonProperty("strain")
    public void setStrain(StrainInfo strain) {
        this.strain = strain;
    }

    public DownloadedReadLibrary withStrain(StrainInfo strain) {
        this.strain = strain;
        return this;
    }

    /**
     * <p>Original spec-file type: SourceInfo</p>
     * <pre>
     * Information about the source of a piece of data.
     * source - the name of the source (e.g. NCBI, JGI, Swiss-Prot)
     * source_id - the ID of the data at the source
     * project_id - the ID of a project encompassing the data at the source
     * @optional source source_id project_id
     * </pre>
     * 
     */
    @JsonProperty("source")
    public SourceInfo getSource() {
        return source;
    }

    /**
     * <p>Original spec-file type: SourceInfo</p>
     * <pre>
     * Information about the source of a piece of data.
     * source - the name of the source (e.g. NCBI, JGI, Swiss-Prot)
     * source_id - the ID of the data at the source
     * project_id - the ID of a project encompassing the data at the source
     * @optional source source_id project_id
     * </pre>
     * 
     */
    @JsonProperty("source")
    public void setSource(SourceInfo source) {
        this.source = source;
    }

    public DownloadedReadLibrary withSource(SourceInfo source) {
        this.source = source;
        return this;
    }

    @JsonProperty("insert_size_mean")
    public java.lang.Double getInsertSizeMean() {
        return insertSizeMean;
    }

    @JsonProperty("insert_size_mean")
    public void setInsertSizeMean(java.lang.Double insertSizeMean) {
        this.insertSizeMean = insertSizeMean;
    }

    public DownloadedReadLibrary withInsertSizeMean(java.lang.Double insertSizeMean) {
        this.insertSizeMean = insertSizeMean;
        return this;
    }

    @JsonProperty("insert_size_std_dev")
    public java.lang.Double getInsertSizeStdDev() {
        return insertSizeStdDev;
    }

    @JsonProperty("insert_size_std_dev")
    public void setInsertSizeStdDev(java.lang.Double insertSizeStdDev) {
        this.insertSizeStdDev = insertSizeStdDev;
    }

    public DownloadedReadLibrary withInsertSizeStdDev(java.lang.Double insertSizeStdDev) {
        this.insertSizeStdDev = insertSizeStdDev;
        return this;
    }

    @JsonProperty("read_count")
    public Long getReadCount() {
        return readCount;
    }

    @JsonProperty("read_count")
    public void setReadCount(Long readCount) {
        this.readCount = readCount;
    }

    public DownloadedReadLibrary withReadCount(Long readCount) {
        this.readCount = readCount;
        return this;
    }

    @JsonProperty("read_size")
    public Long getReadSize() {
        return readSize;
    }

    @JsonProperty("read_size")
    public void setReadSize(Long readSize) {
        this.readSize = readSize;
    }

    public DownloadedReadLibrary withReadSize(Long readSize) {
        this.readSize = readSize;
        return this;
    }

    @JsonProperty("gc_content")
    public java.lang.Double getGcContent() {
        return gcContent;
    }

    @JsonProperty("gc_content")
    public void setGcContent(java.lang.Double gcContent) {
        this.gcContent = gcContent;
    }

    public DownloadedReadLibrary withGcContent(java.lang.Double gcContent) {
        this.gcContent = gcContent;
        return this;
    }

    @JsonProperty("total_bases")
    public Long getTotalBases() {
        return totalBases;
    }

    @JsonProperty("total_bases")
    public void setTotalBases(Long totalBases) {
        this.totalBases = totalBases;
    }

    public DownloadedReadLibrary withTotalBases(Long totalBases) {
        this.totalBases = totalBases;
        return this;
    }

    @JsonProperty("read_length_mean")
    public java.lang.Double getReadLengthMean() {
        return readLengthMean;
    }

    @JsonProperty("read_length_mean")
    public void setReadLengthMean(java.lang.Double readLengthMean) {
        this.readLengthMean = readLengthMean;
    }

    public DownloadedReadLibrary withReadLengthMean(java.lang.Double readLengthMean) {
        this.readLengthMean = readLengthMean;
        return this;
    }

    @JsonProperty("read_length_stdev")
    public java.lang.Double getReadLengthStdev() {
        return readLengthStdev;
    }

    @JsonProperty("read_length_stdev")
    public void setReadLengthStdev(java.lang.Double readLengthStdev) {
        this.readLengthStdev = readLengthStdev;
    }

    public DownloadedReadLibrary withReadLengthStdev(java.lang.Double readLengthStdev) {
        this.readLengthStdev = readLengthStdev;
        return this;
    }

    @JsonProperty("phred_type")
    public java.lang.String getPhredType() {
        return phredType;
    }

    @JsonProperty("phred_type")
    public void setPhredType(java.lang.String phredType) {
        this.phredType = phredType;
    }

    public DownloadedReadLibrary withPhredType(java.lang.String phredType) {
        this.phredType = phredType;
        return this;
    }

    @JsonProperty("number_of_duplicates")
    public Long getNumberOfDuplicates() {
        return numberOfDuplicates;
    }

    @JsonProperty("number_of_duplicates")
    public void setNumberOfDuplicates(Long numberOfDuplicates) {
        this.numberOfDuplicates = numberOfDuplicates;
    }

    public DownloadedReadLibrary withNumberOfDuplicates(Long numberOfDuplicates) {
        this.numberOfDuplicates = numberOfDuplicates;
        return this;
    }

    @JsonProperty("qual_min")
    public java.lang.Double getQualMin() {
        return qualMin;
    }

    @JsonProperty("qual_min")
    public void setQualMin(java.lang.Double qualMin) {
        this.qualMin = qualMin;
    }

    public DownloadedReadLibrary withQualMin(java.lang.Double qualMin) {
        this.qualMin = qualMin;
        return this;
    }

    @JsonProperty("qual_max")
    public java.lang.Double getQualMax() {
        return qualMax;
    }

    @JsonProperty("qual_max")
    public void setQualMax(java.lang.Double qualMax) {
        this.qualMax = qualMax;
    }

    public DownloadedReadLibrary withQualMax(java.lang.Double qualMax) {
        this.qualMax = qualMax;
        return this;
    }

    @JsonProperty("qual_mean")
    public java.lang.Double getQualMean() {
        return qualMean;
    }

    @JsonProperty("qual_mean")
    public void setQualMean(java.lang.Double qualMean) {
        this.qualMean = qualMean;
    }

    public DownloadedReadLibrary withQualMean(java.lang.Double qualMean) {
        this.qualMean = qualMean;
        return this;
    }

    @JsonProperty("qual_stdev")
    public java.lang.Double getQualStdev() {
        return qualStdev;
    }

    @JsonProperty("qual_stdev")
    public void setQualStdev(java.lang.Double qualStdev) {
        this.qualStdev = qualStdev;
    }

    public DownloadedReadLibrary withQualStdev(java.lang.Double qualStdev) {
        this.qualStdev = qualStdev;
        return this;
    }

    @JsonProperty("base_percentages")
    public Map<String, Double> getBasePercentages() {
        return basePercentages;
    }

    @JsonProperty("base_percentages")
    public void setBasePercentages(Map<String, Double> basePercentages) {
        this.basePercentages = basePercentages;
    }

    public DownloadedReadLibrary withBasePercentages(Map<String, Double> basePercentages) {
        this.basePercentages = basePercentages;
        return this;
    }

    @JsonAnyGetter
    public Map<java.lang.String, Object> getAdditionalProperties() {
        return this.additionalProperties;
    }

    @JsonAnySetter
    public void setAdditionalProperties(java.lang.String name, Object value) {
        this.additionalProperties.put(name, value);
    }

    @Override
    public java.lang.String toString() {
        return ((((((((((((((((((((((((((((((((((((((((((((((("DownloadedReadLibrary"+" [files=")+ files)+", ref=")+ ref)+", singleGenome=")+ singleGenome)+", readOrientationOutward=")+ readOrientationOutward)+", sequencingTech=")+ sequencingTech)+", strain=")+ strain)+", source=")+ source)+", insertSizeMean=")+ insertSizeMean)+", insertSizeStdDev=")+ insertSizeStdDev)+", readCount=")+ readCount)+", readSize=")+ readSize)+", gcContent=")+ gcContent)+", totalBases=")+ totalBases)+", readLengthMean=")+ readLengthMean)+", readLengthStdev=")+ readLengthStdev)+", phredType=")+ phredType)+", numberOfDuplicates=")+ numberOfDuplicates)+", qualMin=")+ qualMin)+", qualMax=")+ qualMax)+", qualMean=")+ qualMean)+", qualStdev=")+ qualStdev)+", basePercentages=")+ basePercentages)+", additionalProperties=")+ additionalProperties)+"]");
    }

}
