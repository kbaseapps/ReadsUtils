
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
 * Reads file information.
 * string fwd - the path to the forward / left reads.
 * string rev - the path to the reverse / right reads. null if the reads
 *     are single end or interleaved.
 * string type - one of 'single', 'paired', or 'interleaved'.
 * </pre>
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@Generated("com.googlecode.jsonschema2pojo")
@JsonPropertyOrder({
    "fwd",
    "rev",
    "type"
})
public class ReadsFiles {

    @JsonProperty("fwd")
    private String fwd;
    @JsonProperty("rev")
    private String rev;
    @JsonProperty("type")
    private String type;
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

    @JsonProperty("type")
    public String getType() {
        return type;
    }

    @JsonProperty("type")
    public void setType(String type) {
        this.type = type;
    }

    public ReadsFiles withType(String type) {
        this.type = type;
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
        return ((((((((("ReadsFiles"+" [fwd=")+ fwd)+", rev=")+ rev)+", type=")+ type)+", additionalProperties=")+ additionalProperties)+"]");
    }

}
