
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
 * <p>Original spec-file type: UploadReadsParams</p>
 * <pre>
 * Input to the upload_reads function.
 * Required parameters:
 * fwd_id - the id of the shock node containing the reads data file:
 *     either single end reads, forward/left reads, or interleaved reads.
 * One of:
 * wsid - the id of the workspace where the reads will be saved
 *     (preferred).
 * wsname - the name of the workspace where the reads will be saved.
 * One of:
 * objid - the id of the workspace object to save over
 * name - the name to which the workspace object will be saved
 *     
 * Optional parameters:
 * rev_id - the shock node id containing the reverse/right reads for
 *     paired end, non-interleaved reads.
 * interleaved - specify that the fwd reads file is an interleaved paired
 *     end reads file. Default true, ignored if rev is specified.
 * single_genome - whether the reads are from a single genome or a
 *     metagenome. Default is single genome.
 * read_orientation_outward - whether the read orientation is outward
 *     from the set of primers. Default is false and is ignored for
 *     single end reads.
 * sequencing_tech - the sequencing technology used to produce the
 *     reads.
 * strain - information about the organism strain
 *     that was sequenced.
 * source - information about the organism source.
 * insert_size_mean - the mean size of the genetic fragments. Ignored for
 *     single end reads.
 * insert_size_std_dev - the standard deviation of the size of the
 *     genetic fragments. Ignored for single end reads.
 * read_count - the number of reads in the this dataset.
 * read_size - the total size of the reads, in bases.
 * gc_content - the GC content of the reads.
 * </pre>
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@Generated("com.googlecode.jsonschema2pojo")
@JsonPropertyOrder({
    "fwd_id",
    "wsid",
    "wsname",
    "objid",
    "name",
    "rev_id",
    "interleaved",
    "single_genome",
    "read_orientation_outward",
    "sequencing_tech",
    "strain",
    "source",
    "insert_size_mean",
    "insert_size_std_dev",
    "read_count",
    "read_size",
    "gc_content"
})
public class UploadReadsParams {

    @JsonProperty("fwd_id")
    private String fwdId;
    @JsonProperty("wsid")
    private Long wsid;
    @JsonProperty("wsname")
    private String wsname;
    @JsonProperty("objid")
    private Long objid;
    @JsonProperty("name")
    private String name;
    @JsonProperty("rev_id")
    private String revId;
    @JsonProperty("interleaved")
    private Long interleaved;
    @JsonProperty("single_genome")
    private Long singleGenome;
    @JsonProperty("read_orientation_outward")
    private Long readOrientationOutward;
    @JsonProperty("sequencing_tech")
    private String sequencingTech;
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
    private Double insertSizeMean;
    @JsonProperty("insert_size_std_dev")
    private Double insertSizeStdDev;
    @JsonProperty("read_count")
    private Long readCount;
    @JsonProperty("read_size")
    private Long readSize;
    @JsonProperty("gc_content")
    private Double gcContent;
    private Map<String, Object> additionalProperties = new HashMap<String, Object>();

    @JsonProperty("fwd_id")
    public String getFwdId() {
        return fwdId;
    }

    @JsonProperty("fwd_id")
    public void setFwdId(String fwdId) {
        this.fwdId = fwdId;
    }

    public UploadReadsParams withFwdId(String fwdId) {
        this.fwdId = fwdId;
        return this;
    }

    @JsonProperty("wsid")
    public Long getWsid() {
        return wsid;
    }

    @JsonProperty("wsid")
    public void setWsid(Long wsid) {
        this.wsid = wsid;
    }

    public UploadReadsParams withWsid(Long wsid) {
        this.wsid = wsid;
        return this;
    }

    @JsonProperty("wsname")
    public String getWsname() {
        return wsname;
    }

    @JsonProperty("wsname")
    public void setWsname(String wsname) {
        this.wsname = wsname;
    }

    public UploadReadsParams withWsname(String wsname) {
        this.wsname = wsname;
        return this;
    }

    @JsonProperty("objid")
    public Long getObjid() {
        return objid;
    }

    @JsonProperty("objid")
    public void setObjid(Long objid) {
        this.objid = objid;
    }

    public UploadReadsParams withObjid(Long objid) {
        this.objid = objid;
        return this;
    }

    @JsonProperty("name")
    public String getName() {
        return name;
    }

    @JsonProperty("name")
    public void setName(String name) {
        this.name = name;
    }

    public UploadReadsParams withName(String name) {
        this.name = name;
        return this;
    }

    @JsonProperty("rev_id")
    public String getRevId() {
        return revId;
    }

    @JsonProperty("rev_id")
    public void setRevId(String revId) {
        this.revId = revId;
    }

    public UploadReadsParams withRevId(String revId) {
        this.revId = revId;
        return this;
    }

    @JsonProperty("interleaved")
    public Long getInterleaved() {
        return interleaved;
    }

    @JsonProperty("interleaved")
    public void setInterleaved(Long interleaved) {
        this.interleaved = interleaved;
    }

    public UploadReadsParams withInterleaved(Long interleaved) {
        this.interleaved = interleaved;
        return this;
    }

    @JsonProperty("single_genome")
    public Long getSingleGenome() {
        return singleGenome;
    }

    @JsonProperty("single_genome")
    public void setSingleGenome(Long singleGenome) {
        this.singleGenome = singleGenome;
    }

    public UploadReadsParams withSingleGenome(Long singleGenome) {
        this.singleGenome = singleGenome;
        return this;
    }

    @JsonProperty("read_orientation_outward")
    public Long getReadOrientationOutward() {
        return readOrientationOutward;
    }

    @JsonProperty("read_orientation_outward")
    public void setReadOrientationOutward(Long readOrientationOutward) {
        this.readOrientationOutward = readOrientationOutward;
    }

    public UploadReadsParams withReadOrientationOutward(Long readOrientationOutward) {
        this.readOrientationOutward = readOrientationOutward;
        return this;
    }

    @JsonProperty("sequencing_tech")
    public String getSequencingTech() {
        return sequencingTech;
    }

    @JsonProperty("sequencing_tech")
    public void setSequencingTech(String sequencingTech) {
        this.sequencingTech = sequencingTech;
    }

    public UploadReadsParams withSequencingTech(String sequencingTech) {
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

    public UploadReadsParams withStrain(StrainInfo strain) {
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

    public UploadReadsParams withSource(SourceInfo source) {
        this.source = source;
        return this;
    }

    @JsonProperty("insert_size_mean")
    public Double getInsertSizeMean() {
        return insertSizeMean;
    }

    @JsonProperty("insert_size_mean")
    public void setInsertSizeMean(Double insertSizeMean) {
        this.insertSizeMean = insertSizeMean;
    }

    public UploadReadsParams withInsertSizeMean(Double insertSizeMean) {
        this.insertSizeMean = insertSizeMean;
        return this;
    }

    @JsonProperty("insert_size_std_dev")
    public Double getInsertSizeStdDev() {
        return insertSizeStdDev;
    }

    @JsonProperty("insert_size_std_dev")
    public void setInsertSizeStdDev(Double insertSizeStdDev) {
        this.insertSizeStdDev = insertSizeStdDev;
    }

    public UploadReadsParams withInsertSizeStdDev(Double insertSizeStdDev) {
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

    public UploadReadsParams withReadCount(Long readCount) {
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

    public UploadReadsParams withReadSize(Long readSize) {
        this.readSize = readSize;
        return this;
    }

    @JsonProperty("gc_content")
    public Double getGcContent() {
        return gcContent;
    }

    @JsonProperty("gc_content")
    public void setGcContent(Double gcContent) {
        this.gcContent = gcContent;
    }

    public UploadReadsParams withGcContent(Double gcContent) {
        this.gcContent = gcContent;
        return this;
    }

    @JsonAnyGetter
    public Map<String, Object> getAdditionalProperties() {
        return this.additionalProperties;
    }

    @JsonAnySetter
    public void setAdditionalProperties(String name, Object value) {
        this.additionalProperties.put(name, value);
    }

    @Override
    public String toString() {
        return ((((((((((((((((((((((((((((((((((((("UploadReadsParams"+" [fwdId=")+ fwdId)+", wsid=")+ wsid)+", wsname=")+ wsname)+", objid=")+ objid)+", name=")+ name)+", revId=")+ revId)+", interleaved=")+ interleaved)+", singleGenome=")+ singleGenome)+", readOrientationOutward=")+ readOrientationOutward)+", sequencingTech=")+ sequencingTech)+", strain=")+ strain)+", source=")+ source)+", insertSizeMean=")+ insertSizeMean)+", insertSizeStdDev=")+ insertSizeStdDev)+", readCount=")+ readCount)+", readSize=")+ readSize)+", gcContent=")+ gcContent)+", additionalProperties=")+ additionalProperties)+"]");
    }

}
