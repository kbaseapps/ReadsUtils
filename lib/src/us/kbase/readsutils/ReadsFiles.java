
package us.kbase.readsutils;

import java.util.HashMap;
import java.util.Map;
import javax.annotation.Generated;
import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;


/**
 * <p>Original spec-file type: ReadsFiles</p>
 * <pre>
 * Reads file locations and gzip status.
 * Only the relevant fields will be present in the structure.
 * string fwd - the path to the forward / left reads.
 * string rev - the path to the reverse / right reads.
 * string inter - the path to the interleaved reads.
 * string sing - the path to the single end reads.
 * bool fwd_gz - whether the forward / left reads are gzipped.
 * bool rev_gz - whether the reverse / right reads are gzipped.
 * bool inter_gz - whether the interleaved reads are gzipped.
 * bool sing_gz - whether the single reads are gzipped.
 * </pre>
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@Generated("com.googlecode.jsonschema2pojo")
@JsonPropertyOrder({
    "fwd",
    "rev",
    "inter",
    "sing",
    "fwd_gz",
    "rev_gz",
    "inter_gz",
    "sing_gz"
})
public class ReadsFiles {

    @JsonProperty("fwd")
    private String fwd;
    @JsonProperty("rev")
    private String rev;
    @JsonProperty("inter")
    private String inter;
    @JsonProperty("sing")
    private String sing;
    @JsonProperty("fwd_gz")
    private String fwdGz;
    @JsonProperty("rev_gz")
    private String revGz;
    @JsonProperty("inter_gz")
    private String interGz;
    @JsonProperty("sing_gz")
    private String singGz;
    private Map<String, Object> additionalProperties = new HashMap<String, Object>();

    @JsonProperty("fwd")
    public String getFwd() {
        return fwd;
    }

    @JsonProperty("fwd")
    public void setFwd(String fwd) {
        this.fwd = fwd;
    }

    public ReadsFiles withFwd(String fwd) {
        this.fwd = fwd;
        return this;
    }

    @JsonProperty("rev")
    public String getRev() {
        return rev;
    }

    @JsonProperty("rev")
    public void setRev(String rev) {
        this.rev = rev;
    }

    public ReadsFiles withRev(String rev) {
        this.rev = rev;
        return this;
    }

    @JsonProperty("inter")
    public String getInter() {
        return inter;
    }

    @JsonProperty("inter")
    public void setInter(String inter) {
        this.inter = inter;
    }

    public ReadsFiles withInter(String inter) {
        this.inter = inter;
        return this;
    }

    @JsonProperty("sing")
    public String getSing() {
        return sing;
    }

    @JsonProperty("sing")
    public void setSing(String sing) {
        this.sing = sing;
    }

    public ReadsFiles withSing(String sing) {
        this.sing = sing;
        return this;
    }

    @JsonProperty("fwd_gz")
    public String getFwdGz() {
        return fwdGz;
    }

    @JsonProperty("fwd_gz")
    public void setFwdGz(String fwdGz) {
        this.fwdGz = fwdGz;
    }

    public ReadsFiles withFwdGz(String fwdGz) {
        this.fwdGz = fwdGz;
        return this;
    }

    @JsonProperty("rev_gz")
    public String getRevGz() {
        return revGz;
    }

    @JsonProperty("rev_gz")
    public void setRevGz(String revGz) {
        this.revGz = revGz;
    }

    public ReadsFiles withRevGz(String revGz) {
        this.revGz = revGz;
        return this;
    }

    @JsonProperty("inter_gz")
    public String getInterGz() {
        return interGz;
    }

    @JsonProperty("inter_gz")
    public void setInterGz(String interGz) {
        this.interGz = interGz;
    }

    public ReadsFiles withInterGz(String interGz) {
        this.interGz = interGz;
        return this;
    }

    @JsonProperty("sing_gz")
    public String getSingGz() {
        return singGz;
    }

    @JsonProperty("sing_gz")
    public void setSingGz(String singGz) {
        this.singGz = singGz;
    }

    public ReadsFiles withSingGz(String singGz) {
        this.singGz = singGz;
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
        return ((((((((((((((((((("ReadsFiles"+" [fwd=")+ fwd)+", rev=")+ rev)+", inter=")+ inter)+", sing=")+ sing)+", fwdGz=")+ fwdGz)+", revGz=")+ revGz)+", interGz=")+ interGz)+", singGz=")+ singGz)+", additionalProperties=")+ additionalProperties)+"]");
    }

}
